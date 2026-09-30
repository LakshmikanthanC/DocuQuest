from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserPublic


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
class DocumentPublic(BaseModel):
    id: str
    filename: str
    page_count: int
    chunk_count: int
    size_bytes: int
    status: Literal["ready", "processing", "failed"]
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentPublic]
    total: int


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
class SourceCitation(BaseModel):
    document_id: str
    filename: str
    page: int
    chunk_index: int
    snippet: str
    score: float


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    sources: list[SourceCitation] = Field(default_factory=list)
    created_at: datetime | None = None
    chart: ChartPublic | None = None
    diagram: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    document_ids: list[str] | None = None


class ChartPointPublic(BaseModel):
    # The RAG layer builds `charts.ChartPoint`, so the public schema reads that
    # model directly instead of asking every call site to unpack it first.
    model_config = ConfigDict(from_attributes=True)

    label: str
    value: float


class ChartPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: Literal["bar", "hbar", "line", "pie"]
    title: str = ""
    data: list[ChartPointPublic]


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    has_context: bool
    model: str
    chart: ChartPublic | None = None
    diagram: str | None = None


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessage]
    total: int


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    llm: str
    embedding_model: str
    vector_store: str
    documents: int
    details: dict[str, Any] = Field(default_factory=dict)
