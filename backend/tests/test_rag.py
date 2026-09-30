"""Unit tests for the RAG building blocks (no LLM, no network)."""

from __future__ import annotations

import fitz
import pytest

from app.rag.chunker import build_splitter, split_pages
from app.rag.chain import (
    NO_ANSWER_MESSAGE,
    NO_ANSWER_SENTINEL,
    build_prompt,
    clean_answer,
    format_context,
    generate,
    is_refusal,
)
from app.rag.pdf_loader import clean_text, extract_pages
from app.rag.vector_store import RetrievedChunk


def make_pdf(path, pages: list[str]) -> None:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 100), text, fontsize=11)
    doc.save(str(path))
    doc.close()


# ---------------------------------------------------------------------------
# pdf_loader
# ---------------------------------------------------------------------------
def test_clean_text_normalizes_whitespace_and_blank_lines():
    raw = "Hello    world\r\n\r\n\r\n\r\nSecond   paragraph\t."
    cleaned = clean_text(raw)
    assert cleaned == "Hello world\n\nSecond paragraph ."
    assert "\r" not in cleaned


def test_clean_text_handles_empty_input():
    assert clean_text("") == ""
    assert clean_text("   \n\n  ") == ""


def test_extract_pages_keeps_page_numbers(tmp_path):
    pdf = tmp_path / "sample.pdf"
    make_pdf(pdf, ["Alpha page content", "Beta page content"])

    extracted = extract_pages(pdf)

    assert extracted.page_count == 2
    assert [page.number for page in extracted.pages] == [1, 2]
    assert "Alpha" in extracted.pages[0].text
    assert "Beta" in extracted.pages[1].text


def test_extract_pages_rejects_password_protected_pdf(tmp_path):
    plain = tmp_path / "plain.pdf"
    locked = tmp_path / "locked.pdf"
    make_pdf(plain, ["secret"])

    doc = fitz.open(str(plain))
    doc.save(
        str(locked),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="user",
    )
    doc.close()

    with pytest.raises(ValueError, match="password protected"):
        extract_pages(locked)


# ---------------------------------------------------------------------------
# chunker
# ---------------------------------------------------------------------------
def test_split_pages_assigns_sequential_indexes_and_pages():
    pages = [(1, "alpha " * 400), (2, "beta " * 400)]
    chunks = split_pages(pages)

    assert chunks, "expected chunks to be produced"
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert {chunk.page for chunk in chunks} == {1, 2}
    assert all(chunk.content.strip() for chunk in chunks)


def test_split_pages_drops_blank_pages():
    assert split_pages([(1, "   "), (2, "")]) == []


def test_split_pages_respects_chunk_size_limit():
    chunks = split_pages([(1, "sentence. " * 200)], chunk_size=200, chunk_overlap=20)
    assert chunks
    assert all(len(chunk.content) <= 200 for chunk in chunks)


# ---------------------------------------------------------------------------
# chain prompt / fallback
# ---------------------------------------------------------------------------
def _chunk(content: str = "Machine learning is a subset of AI.", page: int = 3):
    return RetrievedChunk(
        content=content,
        document_id="doc-1",
        filename="research-paper.pdf",
        page=page,
        chunk_index=0,
        score=0.81,
    )


def test_format_context_numbers_and_labels_each_chunk():
    context = format_context([_chunk("first"), _chunk("second", page=7)])
    assert "[1] source: research-paper.pdf (page 3)" in context
    assert "[2] source: research-paper.pdf (page 7)" in context


def test_build_prompt_includes_context_and_question():
    prompt = build_prompt("What is machine learning?", [_chunk()])
    assert "What is machine learning?" in prompt
    assert "Machine learning is a subset of AI." in prompt
    assert NO_ANSWER_SENTINEL in prompt
    assert "ONLY the context" in prompt


# ---------------------------------------------------------------------------
# clean_answer: sentinel handling
# ---------------------------------------------------------------------------
def test_clean_answer_keeps_a_normal_answer():
    assert clean_answer("Machine learning learns from data.") == (
        "Machine learning learns from data.",
        True,
    )


def test_clean_answer_treats_a_lone_sentinel_as_a_refusal():
    answer, has_context = clean_answer(NO_ANSWER_SENTINEL)
    assert has_context is False
    assert answer == NO_ANSWER_MESSAGE


@pytest.mark.parametrize(
    "raw",
    [
        NO_ANSWER_SENTINEL,
        f"  {NO_ANSWER_SENTINEL}  ",
        f"{NO_ANSWER_SENTINEL}.",
        f"Answer: {NO_ANSWER_SENTINEL}",
    ],
)
def test_clean_answer_refusal_variants(raw):
    assert clean_answer(raw)[1] is False


def test_clean_answer_recovers_when_the_model_echoes_then_answers():
    """Small models often echo the sentinel and then answer anyway."""
    answer, has_context = clean_answer(
        f"{NO_ANSWER_SENTINEL}\n\nMachine learning learns patterns from data."
    )
    assert has_context is True
    assert answer == "Machine learning learns patterns from data."
    assert NO_ANSWER_SENTINEL not in answer


@pytest.mark.parametrize(
    "raw",
    [
        "I can't provide an answer to this question as it is not supported by the provided context.",
        "I cannot provide an answer to the question based on the provided context.",
        "I'm sorry, but I don't have that information.",
        "The context does not mention the 1998 World Cup at all.",
        "There is no information about Q3 revenue in these documents.",
        "There is no mention of the airspeed velocity of an unladen swallow in the provided context.",
        "The document does not discuss that topic, so I cannot help here.",
        "The answer is not specified in these pages.",
    ],
)
def test_clean_answer_catches_refusals_written_in_plain_english(raw):
    """Weak models ignore the sentinel, so plain refusals are matched too."""
    answer, has_context = clean_answer(raw)
    assert has_context is False
    assert answer == NO_ANSWER_MESSAGE


def test_clean_answer_keeps_a_real_answer_that_mentions_a_gap():
    """A genuine answer may note a missing detail without being a refusal."""
    raw = (
        "The context does not list Q3 revenue. It does state that Q2 revenue was "
        "$4.2 million, grew 18% quarter over quarter, and that the growth came "
        "mainly from the new enterprise contracts signed in the northern region "
        "during the second quarter, according to the finance summary on page 12."
    )
    answer, has_context = clean_answer(raw)
    assert has_context is True
    assert answer == raw


def test_is_refusal_flags_the_sentinel_anywhere():
    assert is_refusal(f"Blah blah. {NO_ANSWER_SENTINEL}") is True


def test_clean_answer_strips_an_answer_prefix():
    assert clean_answer("Answer: It is a subset of AI.") == ("It is a subset of AI.", True)


def test_clean_answer_handles_empty_output():
    answer, has_context = clean_answer("   ")
    assert has_context is False
    assert answer == NO_ANSWER_MESSAGE


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------
def test_generate_without_context_returns_no_answer_without_calling_llm(monkeypatch):
    def fail_if_called():
        raise AssertionError("LLM must not be called when retrieval is empty")

    monkeypatch.setattr("app.rag.chain.get_llm", fail_if_called)

    result = generate("What is machine learning?", [])
    assert result.has_context is False
    assert result.chunks == []
    assert "could not find an answer" in result.answer.lower()


def test_generate_flags_a_genuine_refusal(monkeypatch):
    class FakeResponse:
        content = NO_ANSWER_SENTINEL

    class FakeLLM:
        def invoke(self, _prompt):
            return FakeResponse()

    monkeypatch.setattr("app.rag.chain.get_llm", lambda: FakeLLM())

    result = generate("What is the revenue?", [_chunk()])
    assert result.has_context is False
    assert result.answer == NO_ANSWER_MESSAGE
    assert result.chunks  # sources are still returned for verification


def test_generate_does_not_flag_an_echoed_sentinel(monkeypatch):
    class FakeResponse:
        content = f"{NO_ANSWER_SENTINEL}\n\nMachine learning learns from data."

    class FakeLLM:
        def invoke(self, _prompt):
            return FakeResponse()

    monkeypatch.setattr("app.rag.chain.get_llm", lambda: FakeLLM())

    result = generate("What is machine learning?", [_chunk()])
    assert result.has_context is True
    assert result.answer == "Machine learning learns from data."


def test_generate_reports_a_friendly_error_when_the_llm_is_down(monkeypatch):
    def explode():
        raise ConnectionError("connection refused")

    monkeypatch.setattr("app.rag.chain.get_llm", explode)

    result = generate("What is machine learning?", [_chunk()])

    assert result.has_context is False
    assert "unavailable" in result.answer.lower()
    assert "ollama" in result.answer.lower()
