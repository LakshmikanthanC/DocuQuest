"""ChromaDB storage, per-user isolation, and score normalisation."""

from __future__ import annotations

import uuid

import pytest

from app.rag import vector_store
from tests.fakes import FakeEmbeddings


@pytest.fixture
def user_id() -> str:
    return f"user-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def embedder() -> FakeEmbeddings:
    return FakeEmbeddings()


def store(user_id: str, name: str, pages: list[tuple[str, int]], embedder) -> str:
    document_id = uuid.uuid4().hex
    vector_store.add_chunks(
        user_id=user_id,
        document_id=document_id,
        filename=name,
        chunks=pages,
        embedding_function=embedder,
    )
    return document_id


def test_add_chunks_returns_stable_ids(user_id, embedder):
    document_id = store(
        user_id, "a.pdf", [("alpha text", 1), ("beta text", 2)], embedder
    )
    assert vector_store.document_chunk_counts(user_id) == {document_id: 2}


def test_add_empty_chunk_list_is_a_noop(user_id, embedder):
    assert vector_store.add_chunks(
        user_id=user_id,
        document_id=uuid.uuid4().hex,
        filename="empty.pdf",
        chunks=[],
        embedding_function=embedder,
    ) == []


def test_similarity_search_ranks_best_match_first(user_id, embedder):
    store(
        user_id,
        "topics.pdf",
        [
            ("Coral reefs host diverse marine life.", 1),
            ("Machine learning models learn patterns from data.", 2),
            ("Pasta needs salted boiling water.", 3),
        ],
        embedder,
    )

    results = vector_store.similarity_search(
        user_id=user_id,
        embedding=embedder.embed_query("machine learning models"),
        top_k=3,
    )

    assert results
    assert results[0].page == 2
    assert "Machine learning" in results[0].content
    assert results[0].filename == "topics.pdf"


def test_scores_are_normalised_to_zero_one(user_id, embedder):
    store(user_id, "a.pdf", [("machine learning", 1)], embedder)

    results = vector_store.similarity_search(
        user_id=user_id, embedding=embedder.embed_query("machine learning"), top_k=1
    )

    assert len(results) == 1
    assert 0.0 <= results[0].score <= 1.0


def test_respects_top_k(user_id, embedder):
    store(user_id, "many.pdf", [(f"chunk number {i}", i + 1) for i in range(6)], embedder)

    results = vector_store.similarity_search(
        user_id=user_id, embedding=embedder.embed_query("chunk"), top_k=2
    )
    assert len(results) == 2


def test_search_is_scoped_to_the_requesting_user(user_id, embedder):
    store(user_id, "mine.pdf", [("my private notes about penguins", 1)], embedder)
    store("someone-else", "theirs.pdf", [("their notes about penguins", 1)], embedder)

    results = vector_store.similarity_search(
        user_id=user_id, embedding=embedder.embed_query("penguins"), top_k=5
    )

    assert len(results) == 1
    assert "my private notes" in results[0].content


def test_document_filter_narrows_results(user_id, embedder):
    marine = store(user_id, "marine.pdf", [("marine life in the ocean", 1)], embedder)
    store(user_id, "cooking.pdf", [("ocean is unrelated to this", 1)], embedder)

    results = vector_store.similarity_search(
        user_id=user_id,
        embedding=embedder.embed_query("ocean"),
        top_k=5,
        document_ids=[marine],
    )

    assert {result.document_id for result in results} == {marine}


def test_delete_document_removes_only_that_document(user_id, embedder):
    keep = store(user_id, "keep.pdf", [("keep this content", 1)], embedder)
    drop = store(user_id, "drop.pdf", [("drop this content", 1)], embedder)

    vector_store.delete_document(user_id, drop)

    remaining = vector_store.similarity_search(
        user_id=user_id, embedding=embedder.embed_query("content"), top_k=10
    )
    assert {result.document_id for result in remaining} == {keep}


def test_delete_user_removes_everything_for_that_user(user_id, embedder):
    store(user_id, "a.pdf", [("alpha", 1)], embedder)
    store(user_id, "b.pdf", [("beta", 1)], embedder)

    vector_store.delete_user(user_id)

    assert vector_store.similarity_search(
        user_id=user_id, embedding=embedder.embed_query("alpha"), top_k=5
    ) == []
    assert user_id not in vector_store.document_chunk_counts(user_id)


def test_document_chunk_counts_of_unknown_user_is_empty(embedder):
    assert vector_store.document_chunk_counts("nobody") == {}
