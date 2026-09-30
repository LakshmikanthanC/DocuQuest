"""Recursive character text splitting with page-aware chunk metadata."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


@dataclass(slots=True)
class Chunk:
    content: str
    page: int
    index: int

    @property
    def length(self) -> int:
        return len(self.content)


def build_splitter(
    chunk_size: int | None = None, chunk_overlap: int | None = None
) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )


def split_pages(
    pages: list[tuple[int, str]],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split ``[(page_number, text), ...]`` into chunks that keep their page number.

    Splitting page-by-page (instead of concatenating first) is what makes source
    citations accurate: every chunk can name the exact page it came from.
    """
    splitter = build_splitter(chunk_size, chunk_overlap)
    chunks: list[Chunk] = []
    for page_number, text in pages:
        for piece in splitter.split_text(text):
            content = piece.strip()
            if not content:
                continue
            chunks.append(
                Chunk(content=content, page=page_number, index=len(chunks))
            )
    return chunks
