from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse
from app.rag import chain, vector_store
from app.services.document_service import get_registry

router = APIRouter(tags=["system"])


@router.get("/cors-origins", include_in_schema=False)
def cors_origins() -> dict[str, list[str]]:
    """Report the configured origins, for diagnosing cross-origin failures."""
    return {"origins": settings.cors_origin_list}


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        documents = get_registry().count_all()
        vector_store_error = None
        total_chunks = vector_store.total_chunks()
    except Exception as exc:
        documents = 0
        total_chunks = 0
        vector_store_error = str(exc)

    llm_up = chain.llm_is_available()
    return HealthResponse(
        status="ok",
        llm=f"{settings.llm_model} ({'online' if llm_up else 'offline'})",
        embedding_model=settings.embedding_model,
        vector_store="chroma",
        documents=documents,
        details={
            "ollama_url": settings.ollama_base_url,
            "chroma_path": str(settings.chroma_persist_directory),
            "total_chunks": total_chunks,
            "vector_store_error": vector_store_error,
        },
    )
