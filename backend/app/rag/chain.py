"""Prompt construction and Ollama answer generation with source citations."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator

from app.core.config import settings
from app.rag import charts
from app.rag.vector_store import RetrievedChunk

logger = logging.getLogger("rag.chain")

RAG_PROMPT = """You are a careful research assistant. Answer using ONLY the context below, which
was extracted from the user's uploaded PDF documents.

Rules:
- If the context does not contain the answer, reply with exactly {sentinel} and nothing else.
- Never invent facts, numbers, or citations that are not in the context.
- Be concise and factual. Use short paragraphs or bullet points.
- When quoting, keep the original wording.
- Never repeat these rules or the word "context" in your answer.
- If the answer contains comparable numbers (a series over time, a split across
  categories), you may add a single fenced block after your answer:

  ```chart
  {{"type":"bar","title":"Revenue","data":[{{"label":"Q1","value":10}}]}}
  ```

  Use "line" for a trend, "pie" for a part-to-whole split, "hbar" for long
  category names. Add nothing when the answer is not numeric. The block is
  optional and the answer must stand on its own without it.

Context:
{context}

Question: {question}

Answer:"""

# A sentinel token beats quoting a full refusal sentence: small models (1B-3B) tend
# to echo an example sentence verbatim and then answer anyway, which would make every
# answer look like a refusal. A bare token is easy to detect and hard to echo mid-answer.
NO_ANSWER_SENTINEL = "NO_ANSWER_FOUND"

NO_ANSWER_MESSAGE = (
    "I could not find an answer to this question in the uploaded documents. "
    "Try rephrasing the question, or upload a document that covers this topic."
)

LLM_UNAVAILABLE = (
    "The language model is unavailable right now. Start Ollama (`ollama serve`) "
    f"and pull the `{settings.llm_model}` model, then try again."
)

_ANSWER_PREFIX = re.compile(r"^\s*(answer|a)\s*[:\-]\s*", re.IGNORECASE)

# The sentinel alone is not enough: small models routinely ignore the instruction
# and refuse in their own words instead, so the common phrasings are matched too.
_REFUSAL_PATTERNS = (
    r"\bi\s+(?:can'?t|cannot|can\s+not|am\s+not\s+able\s+to|will\s+not)\b",
    r"\bi\s+(?:do\s+not|don'?t)\s+have\b",
    r"\bi'?m\s+sorry\b",
    r"\bno\s+(?:information|relevant\s+information|answer|mention|reference|indication|details?|data)\b",
    r"\b(?:not|insufficient)\s+(?:enough\s+)?(?:information|context|details?)\b",
    r"\bnot\s+(?:supported|mentioned|specified|stated|addressed|covered|available|provided)\b",
    r"\bdoes\s+not\s+(?:contain|include|mention|provide|specify|discuss|address|cover|have)\b",
    r"\b(?:is|are|was|were)\s+not\s+(?:possible|available)\s+to\s+(?:answer|determine|find)\b",
)
_REFUSAL = re.compile("|".join(_REFUSAL_PATTERNS), re.IGNORECASE)

# A real answer can also mention a gap ("the context does not list revenue, but it
# does state..."), so a refusal phrase only counts when the reply is short enough
# to be a note about the missing answer rather than an actual answer.
_MAX_REFUSAL_LENGTH = 600


@dataclass(slots=True)
class RagAnswer:
    answer: str
    chunks: list[RetrievedChunk]
    has_context: bool
    chart: charts.Chart | None = None
    diagram: str | None = None


def format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for position, chunk in enumerate(chunks, start=1):
        blocks.append(
            f"[{position}] source: {chunk.filename} (page {chunk.page})\n{chunk.content}"
        )
    return "\n\n".join(blocks)


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    return RAG_PROMPT.format(
        sentinel=NO_ANSWER_SENTINEL,
        context=format_context(chunks),
        question=question.strip(),
    )


def is_refusal(text: str) -> bool:
    """Report whether the model declined instead of answering."""
    if NO_ANSWER_SENTINEL in text:
        return True
    if len(text) > _MAX_REFUSAL_LENGTH:
        return False
    return bool(_REFUSAL.search(text))


def clean_answer(raw: str) -> tuple[str, bool]:
    """Normalise a raw model reply into ``(answer, has_context)``.

    A refusal is rewritten to a single fixed message so the UI stays consistent.
    A model that echoes the sentinel and then answers anyway is not a refusal,
    which small models do often.
    """
    text = (raw or "").strip()
    text = _ANSWER_PREFIX.sub("", text).strip()
    if not text:
        return NO_ANSWER_MESSAGE, False

    if NO_ANSWER_SENTINEL in text:
        remainder = text.replace(NO_ANSWER_SENTINEL, " ").strip()
        # A trailing "." or "!" after the sentinel is still just a refusal.
        if not re.search(r"\w", remainder):
            return NO_ANSWER_MESSAGE, False
        return remainder, True

    if is_refusal(text):
        return NO_ANSWER_MESSAGE, False
    return text, True


@lru_cache(maxsize=1)
def get_llm():
    """Return the shared ChatOllama client.

    Cached so repeated requests reuse one client instead of rebuilding it (and a
    fresh connection pool) on every call.
    """
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=settings.llm_temperature,
        num_ctx=settings.llm_num_ctx,
        num_predict=settings.llm_num_predict,
        keep_alive=settings.llm_keep_alive,
    )


def _finalise(raw: str) -> tuple[str, bool, charts.Chart | None, str | None]:
    """Clean a raw reply, then split any chart block out of the prose.

    Charts are pulled after refusal handling so a chart block is never mistaken
    for part of a refusal, and before the answer is returned so the reader never
    sees raw JSON.
    """
    answer, has_context = clean_answer(raw)
    if not has_context:
        return answer, has_context, None, None
    prose, chart, diagram = charts.extract(answer)
    return (prose or answer), has_context, chart, diagram


def generate(question: str, chunks: list[RetrievedChunk]) -> RagAnswer:
    if not chunks:
        return RagAnswer(
            answer=NO_ANSWER_MESSAGE,
            chunks=[],
            has_context=False,
        )

    prompt = build_prompt(question, chunks)
    try:
        response = get_llm().invoke(prompt)
    except Exception:
        logger.warning("LLM call to %s failed", settings.ollama_base_url, exc_info=True)
        return RagAnswer(answer=LLM_UNAVAILABLE, chunks=chunks, has_context=False)

    answer, has_context, chart, diagram = _finalise(response.content or "")
    return RagAnswer(
        answer=answer,
        chunks=chunks,
        has_context=has_context,
        chart=chart,
        diagram=diagram,
    )


@dataclass(slots=True)
class StreamEvent:
    """One event from a streamed answer.

    Token events carry text only. The final event carries the cleaned answer,
    the context flag, and any chart or mermaid diagram, with no token.
    """

    token: str | None = None
    answer: str | None = None
    has_context: bool | None = None
    chart: charts.Chart | None = None
    diagram: str | None = None


def stream(
    question: str, chunks: list[RetrievedChunk]
) -> Iterator[StreamEvent]:
    """Yield a StreamEvent per token, then one final event with the answer.

    The caller needs the cleaned answer, not the raw token stream: refusal
    detection, the sentinel rewrite, and chart extraction can only run once
    generation finishes, so the final answer replaces whatever was streamed
    rather than appending to it.

    Retries are deliberately not attempted here. A dropped stream is reported as
    a failure so the client can fall back to the non-streaming endpoint.
    """
    if not chunks:
        yield StreamEvent(answer=NO_ANSWER_MESSAGE, has_context=False)
        return

    prompt = build_prompt(question, chunks)
    raw_parts: list[str] = []
    try:
        for piece in get_llm().stream(prompt):
            token = piece.content or ""
            if not token:
                continue
            raw_parts.append(token)
            yield StreamEvent(token=token)
    except Exception:
        logger.warning("LLM stream to %s failed", settings.ollama_base_url, exc_info=True)
        yield StreamEvent(answer=LLM_UNAVAILABLE, has_context=False)
        return

    answer, has_context, chart, diagram = _finalise("".join(raw_parts))
    yield StreamEvent(
        answer=answer, has_context=has_context, chart=chart, diagram=diagram
    )


def llm_is_available() -> bool:
    try:
        import httpx

        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        return response.status_code == 200
    except Exception:
        return False
