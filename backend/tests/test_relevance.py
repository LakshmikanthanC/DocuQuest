"""The retrieval relevance floor: weak matches are dropped before the LLM.

The fake embedder produces a cosine-like score, so a question sharing no words
with a chunk scores near zero. That is enough to test the floor end to end
without the real embedding model.
"""

from __future__ import annotations

import uuid

import fitz
import pytest

from app.core.config import settings
from app.rag import vector_store
from tests.fakes import FakeEmbeddings


@pytest.fixture
def user_id() -> str:
    return f"user-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def embedder() -> FakeEmbeddings:
    return FakeEmbeddings()


def test_matching_question_clears_the_floor(user_id, embedder):
    document_id = uuid.uuid4().hex
    vector_store.add_chunks(
        user_id=user_id,
        document_id=document_id,
        filename="topics.pdf",
        chunks=[("Machine learning learns patterns from data.", 1)],
        embedding_function=embedder,
    )

    hits = vector_store.similarity_search(
        user_id=user_id,
        embedding=embedder.embed_query("What is machine learning?"),
        top_k=3,
        min_score=settings.min_relevance_score,
    )

    assert hits, "a topically matching chunk must survive the floor"
    assert hits[0].document_id == document_id


def test_unrelated_question_is_dropped(user_id, embedder):
    vector_store.add_chunks(
        user_id=user_id,
        document_id=uuid.uuid4().hex,
        filename="topics.pdf",
        chunks=[("Coral reefs host diverse marine life.", 1)],
        embedding_function=embedder,
    )

    hits = vector_store.similarity_search(
        user_id=user_id,
        embedding=embedder.embed_query("quarterly revenue and payroll figures"),
        top_k=3,
        min_score=settings.min_relevance_score,
    )

    assert hits == [], "a question sharing no words with the corpus is not answerable"


def test_a_zero_floor_returns_everything(user_id, embedder):
    """The floor must be what filters chunks, not the search itself."""
    vector_store.add_chunks(
        user_id=user_id,
        document_id=uuid.uuid4().hex,
        filename="topics.pdf",
        chunks=[("Coral reefs host diverse marine life.", 1)],
        embedding_function=embedder,
    )

    unfiltered = vector_store.similarity_search(
        user_id=user_id,
        embedding=embedder.embed_query("quarterly revenue and payroll figures"),
        top_k=3,
        min_score=0.0,
    )

    assert unfiltered, "Chroma returns nearest neighbours even when they are poor"
    assert unfiltered[0].score < settings.min_relevance_score


def test_floor_is_above_the_hyperbolic_ceiling_of_a_non_match(user_id, embedder):
    """Guard the arithmetic behind the default.

    ``score = 1 / (1 + squared_l2)`` bottoms out at 1/3 for normalised vectors,
    so a floor below that would silently never fire.
    """
    orthogonal = 1.0 / (1.0 + 2.0)
    assert settings.min_relevance_score > orthogonal, (
        f"min_relevance_score={settings.min_relevance_score} is below the {orthogonal:.3f} "
        "floor of the score transform, so it can never reject an unrelated chunk"
    )


def test_floor_never_reorders_survivors(user_id, embedder):
    vector_store.add_chunks(
        user_id=user_id,
        document_id=uuid.uuid4().hex,
        filename="topics.pdf",
        chunks=[
            ("Machine learning models learn patterns from data.", 1),
            ("Machine learning requires labelled training data.", 2),
        ],
        embedding_function=embedder,
    )
    query = embedder.embed_query("What does machine learning need?")

    unfiltered = vector_store.similarity_search(
        user_id=user_id, embedding=query, top_k=2, min_score=0.0
    )
    filtered = vector_store.similarity_search(
        user_id=user_id,
        embedding=query,
        top_k=2,
        min_score=settings.min_relevance_score,
    )

    assert [c.chunk_index for c in filtered] == [
        c.chunk_index for c in unfiltered if c.score >= settings.min_relevance_score
    ]
    scores = [c.score for c in filtered]
    assert scores == sorted(scores, reverse=True)


def test_chat_reports_no_context_when_nothing_clears_the_floor(
    client, auth, offline_models
):
    """End to end: an unrelated question must not reach the model at all."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Coral reefs host diverse marine life.", fontsize=11)
    data = doc.tobytes()
    doc.close()

    response = client.post(
        "/api/documents",
        headers=auth,
        files={"file": ("reefs.pdf", data, "application/pdf")},
    )
    assert response.status_code == 201, response.text

    body = client.post(
        "/api/chat",
        headers=auth,
        json={"question": "What were the quarterly payroll and revenue figures?"},
    ).json()

    assert body["has_context"] is False
    assert body["sources"] == []
    assert "could not find an answer" in body["answer"].lower()
    assert offline_models.prompts == [], "the LLM should not be called at all"
