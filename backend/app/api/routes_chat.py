import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.schemas import (
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    SourceCitation,
)
from app.rag import chain, vector_store
from app.rag.embeddings import embed_query
from app.services import chat_service, document_service
from app.services.document_service import get_registry

logger = logging.getLogger("rag.chat")

router = APIRouter(prefix="/chat", tags=["chat"])

SNIPPET_CHARS = 320


def _to_citation(chunk: vector_store.RetrievedChunk) -> SourceCitation:
    snippet = chunk.content[:SNIPPET_CHARS]
    if len(chunk.content) > SNIPPET_CHARS:
        snippet = f"{snippet}..."
    return SourceCitation(
        document_id=chunk.document_id,
        filename=chunk.filename,
        page=chunk.page,
        chunk_index=chunk.chunk_index,
        snippet=snippet,
        score=chunk.score,
    )


def _retrieve(user_id: str, payload: ChatRequest) -> list[vector_store.RetrievedChunk]:
    """Validate the request and return the retrieved chunks.

    Shared by the buffered and streaming routes so both reject the same inputs.
    """
    if payload.document_ids:
        known = {record.id for record in get_registry().get_many(user_id, payload.document_ids)}
        unknown = set(payload.document_ids) - known
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown document ids: {', '.join(sorted(unknown))}",
            )

    if get_registry().count_for_user(user_id) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a PDF document before asking questions",
        )

    top_k = payload.top_k or settings.retrieval_top_k
    try:
        embedding = embed_query(payload.question)
    except Exception:
        logger.exception("Embedding model unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"The embedding model `{settings.embedding_model}` could not be loaded. "
                "Check the backend logs and your network connection to Hugging Face."
            ),
        ) from None

    chunks = vector_store.similarity_search(
        user_id=user_id,
        embedding=embedding,
        top_k=top_k,
        document_ids=payload.document_ids,
        min_score=settings.min_relevance_score,
    )
    if not chunks:
        # Nothing cleared the relevance floor, so there is no context to answer
        # from. Reporting this here means the model is never asked to decline.
        logger.info(
            "No chunk for user=%s cleared the %.2f relevance floor; "
            "top_k=%d documents=%d",
            user_id,
            settings.min_relevance_score,
            top_k,
            len(payload.document_ids or []),
        )
    return chunks


@router.post("", response_model=ChatResponse)
def ask_question(
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    user_id = current_user["id"]
    chat_service.add_message(user_id, "user", payload.question)

    chunks = _retrieve(user_id, payload)
    result = chain.generate(payload.question, chunks)
    citations = [_to_citation(chunk) for chunk in result.chunks]
    chat_service.add_message(
        user_id,
        "assistant",
        result.answer,
        citations,
        chart=result.chart,
        diagram=result.diagram,
    )

    return ChatResponse(
        answer=result.answer,
        sources=citations,
        has_context=result.has_context,
        model=settings.llm_model,
        chart=result.chart,
        diagram=result.diagram,
    )


def _sse(event: str, data: dict) -> str:
    """Encode one server-sent event.

    JSON is used rather than bare lines because answers contain newlines.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
def stream_answer(
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the answer as server-sent events.

    Retrieval is done up front so validation errors still surface as normal HTTP
    status codes instead of being buried inside a 200 stream.
    """
    user_id = current_user["id"]
    chunks = _retrieve(user_id, payload)
    citations = [_to_citation(chunk) for chunk in chunks]
    chat_service.add_message(user_id, "user", payload.question)

    def event_stream() -> Iterator[str]:
        yield _sse(
            "sources",
            {
                "sources": [citation.model_dump() for citation in citations],
                "model": settings.llm_model,
            },
        )

        final_answer: str | None = None
        has_context = False
        chart = None
        diagram = None
        for event in chain.stream(payload.question, chunks):
            if event.answer is not None:
                final_answer = event.answer
                has_context = bool(event.has_context)
                chart = event.chart
                diagram = event.diagram
                break
            if event.token:
                yield _sse("token", {"text": event.token})

        if final_answer is None:
            final_answer = chain.LLM_UNAVAILABLE

        chat_service.add_message(
            user_id, "assistant", final_answer, citations, chart=chart, diagram=diagram
        )
        yield _sse(
            "done",
            {
                "answer": final_answer,
                "has_context": has_context,
                "model": settings.llm_model,
                "chart": chart.model_dump() if chart else None,
                "diagram": diagram,
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Nginx buffers SSE by default, which would defeat the point.
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=ChatHistoryResponse)
def history(current_user: dict = Depends(get_current_user)) -> ChatHistoryResponse:
    messages: list[ChatMessage] = chat_service.get_history(current_user["id"])
    return ChatHistoryResponse(messages=messages, total=len(messages))


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(current_user: dict = Depends(get_current_user)) -> None:
    chat_service.clear_history(current_user["id"])


@router.delete("/history/all", status_code=status.HTTP_204_NO_CONTENT)
def delete_account_data(current_user: dict = Depends(get_current_user)) -> None:
    user_id = current_user["id"]
    document_service.delete_user_documents(user_id)
    vector_store.delete_user(user_id)
    chat_service.clear_history(user_id)
