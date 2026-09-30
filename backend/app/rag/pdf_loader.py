"""PDF loading and per-page text extraction built on PyMuPDF."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

_WHITESPACE = re.compile(r"[ \t\u00a0]+")
_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(slots=True)
class Page:
    number: int
    text: str


@dataclass(slots=True)
class ExtractedDocument:
    filename: str
    page_count: int
    pages: list[Page] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


def extract_pages(pdf_path: str | Path, filename: str | None = None) -> ExtractedDocument:
    """Return one cleaned text block per page. Pages without text are dropped."""
    path = Path(pdf_path)
    with fitz.open(path) as doc:
        if doc.needs_pass:
            raise ValueError("PDF is password protected")
        pages: list[Page] = []
        for index, page in enumerate(doc, start=1):
            text = clean_text(page.get_text("text"))
            if text:
                pages.append(Page(number=index, text=text))
        return ExtractedDocument(
            filename=filename or path.name,
            page_count=doc.page_count,
            pages=pages,
        )
