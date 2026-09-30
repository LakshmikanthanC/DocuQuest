"""PDF upload, indexing into ChromaDB, and document lifecycle management."""

from __future__ import annotations

import shutil
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.core.config import settings
from app.rag import vector_store
from app.rag.chunker import split_pages
from app.rag.embeddings import get_embeddings
from app.rag.pdf_loader import extract_pages
from app.services.json_store import read_json_list, write_json_atomically

INDEX_FILE = "documents.json"
_lock = threading.RLock()


@dataclass(slots=True)
class DocumentRecord:
    id: str
    user_id: str
    filename: str
    stored_name: str
    size_bytes: int
    page_count: int
    chunk_count: int
    status: str = "ready"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("user_id")
        data.pop("stored_name")
        return data


class DocumentRegistry:
    """Tracks uploaded documents and their on-disk copies."""

    def __init__(self) -> None:
        self._path = settings.upload_directory / INDEX_FILE
        self._records: dict[str, DocumentRecord] = {}
        self._load()

    def _load(self) -> None:
        loaded = read_json_list(self._path, "document")
        if loaded is None:
            return
        self._records = {item["id"]: DocumentRecord(**item) for item in loaded}

    def _flush(self) -> None:
        write_json_atomically(
            self._path, [asdict(record) for record in self._records.values()]
        )

    def list_for_user(self, user_id: str) -> list[DocumentRecord]:
        with _lock:
            records = [r for r in self._records.values() if r.user_id == user_id]
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def get(self, user_id: str, document_id: str) -> DocumentRecord | None:
        with _lock:
            record = self._records.get(document_id)
        if record is None or record.user_id != user_id:
            return None
        return record

    def get_many(self, user_id: str, document_ids: list[str]) -> list[DocumentRecord]:
        return [
            record
            for document_id in document_ids
            if (record := self.get(user_id, document_id)) is not None
        ]

    def add(self, record: DocumentRecord) -> None:
        with _lock:
            self._records[record.id] = record
            self._flush()

    def update(self, document_id: str, **changes: Any) -> None:
        with _lock:
            record = self._records.get(document_id)
            if record is None:
                return
            for key, value in changes.items():
                setattr(record, key, value)
            self._flush()

    def remove(self, user_id: str, document_id: str) -> DocumentRecord | None:
        with _lock:
            record = self._records.get(document_id)
            if record is None or record.user_id != user_id:
                return None
            del self._records[document_id]
            self._flush()
            return record

    def count_for_user(self, user_id: str) -> int:
        return len(self.list_for_user(user_id))

    def count_all(self) -> int:
        with _lock:
            return len(self._records)


_registry: DocumentRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> DocumentRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = DocumentRegistry()
        return _registry


def user_upload_dir(user_id: str) -> Path:
    path = settings.upload_directory / user_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_pdf(filename: str, content_type: str | None) -> bool:
    return filename.lower().endswith(".pdf") or (content_type or "").endswith("pdf")


def index_document(record: DocumentRecord) -> DocumentRecord:
    """Extract, chunk, embed, and store a previously saved PDF."""
    source = user_upload_dir(record.user_id) / record.stored_name
    extracted = extract_pages(source, filename=record.filename)
    chunks = split_pages([(page.number, page.text) for page in extracted.pages])

    vector_store.add_chunks(
        user_id=record.user_id,
        document_id=record.id,
        filename=record.filename,
        chunks=[(chunk.content, chunk.page) for chunk in chunks],
        embedding_function=get_embeddings(),
    )

    registry = get_registry()
    registry.update(
        record.id,
        page_count=extracted.page_count,
        chunk_count=len(chunks),
        status="ready",
    )
    return registry.get(record.user_id, record.id) or record


async def save_upload(user_id: str, upload: UploadFile) -> DocumentRecord:
    filename = Path(upload.filename or "document.pdf").name
    if not is_pdf(filename, upload.content_type):
        raise ValueError("Only PDF files are supported")

    document_id = uuid.uuid4().hex
    stored_name = f"{document_id}.pdf"
    destination = user_upload_dir(user_id) / stored_name

    size = 0
    with destination.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                handle.close()
                destination.unlink(missing_ok=True)
                raise ValueError(
                    f"File exceeds the {settings.max_upload_mb} MB upload limit"
                )
            handle.write(chunk)

    if size == 0:
        destination.unlink(missing_ok=True)
        raise ValueError("Uploaded file is empty")

    record = DocumentRecord(
        id=document_id,
        user_id=user_id,
        filename=filename,
        stored_name=stored_name,
        size_bytes=size,
        page_count=0,
        chunk_count=0,
        status="processing",
    )
    get_registry().add(record)
    return record


def delete_document(user_id: str, document_id: str) -> bool:
    registry = get_registry()
    record = registry.remove(user_id, document_id)
    if record is None:
        return False
    target = user_upload_dir(user_id) / record.stored_name
    target.unlink(missing_ok=True)
    try:
        vector_store.delete_document(user_id, document_id)
    except Exception:
        pass
    return True


def delete_user_documents(user_id: str) -> None:
    for record in get_registry().list_for_user(user_id):
        delete_document(user_id, record.id)
    shutil.rmtree(settings.upload_directory / user_id, ignore_errors=True)
