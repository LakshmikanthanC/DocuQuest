"""ChromaDB persistence layer: one collection, namespaced by user id."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError
from langchain_chroma import Chroma

from app.core.config import settings

COLLECTION_NAME = "rag_chunks"

_lock = threading.Lock()
_client: chromadb.ClientAPI | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    with _lock:
        if _client is None:
            _client = chromadb.PersistentClient(
                path=str(settings.chroma_persist_directory),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
            )
        return _client


def _where(user_id: str, document_ids: list[str] | None) -> dict[str, Any]:
    """Chroma rejects multiple top-level filter keys, so combine with ``$and``."""
    if not document_ids:
        return {"user_id": user_id}
    return {
        "$and": [
            {"user_id": user_id},
            {"document_id": {"$in": list(document_ids)}},
        ]
    }


@dataclass(slots=True)
class RetrievedChunk:
    content: str
    document_id: str
    filename: str
    page: int
    chunk_index: int
    score: float


def get_store(embedding_function: Any = None) -> Chroma:
    return Chroma(
        client=get_client(),
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_function,
    )


def add_chunks(
    *,
    user_id: str,
    document_id: str,
    filename: str,
    chunks: list[tuple[str, int]],
    embedding_function: Any,
) -> list[str]:
    """Store ``[(content, page), ...]`` and return the generated chunk ids."""
    if not chunks:
        return []
    ids = [f"{document_id}:{index}" for index in range(len(chunks))]
    metadatas = [
        {
            "user_id": user_id,
            "document_id": document_id,
            "filename": filename,
            "page": page,
            "chunk_index": index,
        }
        for index, (_content, page) in enumerate(chunks)
    ]
    get_store(embedding_function).add_texts(
        texts=[content for content, _page in chunks],
        metadatas=metadatas,
        ids=ids,
    )
    return ids


def delete_document(user_id: str, document_id: str) -> None:
    client = get_client()
    client.get_collection(COLLECTION_NAME).delete(
        where={
            "$and": [{"user_id": user_id}, {"document_id": document_id}],
        }
    )


def delete_user(user_id: str) -> None:
    get_client().get_collection(COLLECTION_NAME).delete(where={"user_id": user_id})


def similarity_search(
    *,
    user_id: str,
    embedding: list[float],
    top_k: int,
    document_ids: list[str] | None = None,
    min_score: float = 0.0,
) -> list[RetrievedChunk]:
    """Return up to ``top_k`` chunks scoring at least ``min_score``.

    Chroma always returns the ``n_results`` nearest neighbours, even when every
    one of them is a poor match, so an unrelated question still hands the model
    four irrelevant chunks. ``min_score`` drops those first.
    """
    client = get_client()
    collection = client.get_collection(COLLECTION_NAME)
    result = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=_where(user_id, document_ids),
        include=["documents", "metadatas", "distances"],
    )

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    retrieved: list[RetrievedChunk] = []
    for content, metadata, distance in zip(documents, metadatas, distances):
        if not content or not metadata:
            continue
        # Chroma returns squared L2 distance; convert to 0..1 similarity
        score = round(1.0 / (1.0 + float(distance)), 4)
        if score < min_score:
            continue
        retrieved.append(
            RetrievedChunk(
                content=content,
                document_id=str(metadata.get("document_id", "")),
                filename=str(metadata.get("filename", "")),
                page=int(metadata.get("page", 0) or 0),
                chunk_index=int(metadata.get("chunk_index", 0) or 0),
                score=score,
            )
        )
    return retrieved


def document_chunk_counts(user_id: str) -> dict[str, int]:
    client = get_client()
    collection = client.get_collection(COLLECTION_NAME)
    counts: dict[str, int] = {}
    offset = 0
    limit = 1000
    while True:
        batch = collection.get(where={"user_id": user_id}, limit=limit, offset=offset)
        metadatas = batch.get("metadatas") or []
        for metadata in metadatas:
            if not metadata:
                continue
            document_id = str(metadata.get("document_id", ""))
            counts[document_id] = counts.get(document_id, 0) + 1
        if len(metadatas) < limit:
            break
        offset += limit
    return counts


def total_chunks() -> int:
    try:
        return get_client().get_collection(COLLECTION_NAME).count()
    except NotFoundError:
        return 0
