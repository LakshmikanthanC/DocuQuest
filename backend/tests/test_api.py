"""API-level tests.

The LLM and the embedding model are fakes, so the suite runs offline, but the
real pipeline runs: PyMuPDF extraction, chunking, ChromaDB storage, similarity
search, and the full request/response contract.
"""

from __future__ import annotations

import uuid

import fitz
from fastapi.testclient import TestClient

from app.core.config import settings

ANSWER = "Machine learning is a subset of artificial intelligence."


def make_pdf_bytes(pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 100), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def upload(client: TestClient, auth: dict, name: str, pages: list[str]) -> dict:
    response = client.post(
        "/api/documents",
        headers=auth,
        files={"file": (name, make_pdf_bytes(pages), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------
def test_health_endpoint_is_public(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["vector_store"] == "chroma"
    assert "online" in body["llm"]


def test_root_endpoint(client: TestClient):
    assert client.get("/").json()["health"] == "/api/health"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def test_register_then_login_returns_token(client: TestClient, credentials: dict):
    created = client.post("/api/auth/register", json=credentials)
    assert created.status_code == 201
    assert created.json()["user"]["email"] == credentials["email"]

    login = client.post("/api/auth/login", json=credentials)
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_register_duplicate_email_conflicts(client: TestClient, auth: dict, credentials: dict):
    assert client.post("/api/auth/register", json=credentials).status_code == 409


def test_register_rejects_short_password(client: TestClient):
    response = client.post(
        "/api/auth/register", json={"email": "a@b.com", "password": "short"}
    )
    assert response.status_code == 422


def test_login_with_wrong_password_is_unauthorized(client: TestClient, auth: dict, credentials: dict):
    response = client.post(
        "/api/auth/login", json={**credentials, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_me_requires_token(client: TestClient):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_forged_token(client: TestClient):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer forged.token.value"}
    )
    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient, auth: dict, credentials: dict):
    response = client.get("/api/auth/me", headers=auth)
    assert response.status_code == 200
    assert response.json()["email"] == credentials["email"]


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
def test_documents_require_authentication(client: TestClient):
    assert client.get("/api/documents").status_code == 401
    assert client.post("/api/documents", files={}).status_code == 401


def test_upload_pdf_indexes_and_appears_in_list(client: TestClient, auth: dict):
    upload(client, auth, "research.pdf", ["Machine learning page one", "Deep learning page two"])

    listing = client.get("/api/documents", headers=auth).json()
    assert listing["total"] == 1

    document = listing["documents"][0]
    assert document["filename"] == "research.pdf"
    assert document["status"] == "ready"
    assert document["page_count"] == 2
    assert document["chunk_count"] > 0
    assert document["size_bytes"] > 0


def test_upload_rejects_non_pdf(client: TestClient, auth: dict):
    response = client.post(
        "/api/documents",
        headers=auth,
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_upload_rejects_empty_file(client: TestClient, auth: dict):
    response = client.post(
        "/api/documents",
        headers=auth,
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_delete_document_removes_it(client: TestClient, auth: dict):
    document = upload(client, auth, "temp.pdf", ["to be deleted"])

    assert client.delete(f"/api/documents/{document['id']}", headers=auth).status_code == 204
    assert client.get("/api/documents", headers=auth).json()["total"] == 0


def test_delete_unknown_document_is_404(client: TestClient, auth: dict):
    assert client.delete("/api/documents/does-not-exist", headers=auth).status_code == 404


def test_documents_are_isolated_per_user(client: TestClient, auth: dict):
    document = upload(client, auth, "private.pdf", ["private doc"])

    other_token = client.post(
        "/api/auth/register",
        json={"email": f"other-{uuid.uuid4().hex[:8]}@example.com", "password": "supersecret"},
    ).json()["access_token"]
    other = {"Authorization": f"Bearer {other_token}"}

    assert client.get("/api/documents", headers=other).json()["total"] == 0
    assert client.delete(f"/api/documents/{document['id']}", headers=other).status_code == 404


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def test_chat_requires_documents(client: TestClient, auth: dict):
    response = client.post("/api/chat", headers=auth, json={"question": "hello?"})
    assert response.status_code == 400
    assert "Upload a PDF" in response.json()["detail"]


def test_chat_requires_authentication(client: TestClient):
    assert client.post("/api/chat", json={"question": "hello?"}).status_code == 401


def test_chat_rejects_empty_question(client: TestClient, auth: dict):
    response = client.post("/api/chat", headers=auth, json={"question": ""})
    assert response.status_code == 422


def test_chat_rejects_unknown_document_filter(client: TestClient, auth: dict):
    upload(client, auth, "doc.pdf", ["content"])

    response = client.post(
        "/api/chat",
        headers=auth,
        json={"question": "What is ML?", "document_ids": ["nope"]},
    )
    assert response.status_code == 404
    assert "Unknown document ids" in response.json()["detail"]


def test_chat_retrieves_real_chunks_and_cites_the_page(client: TestClient, auth: dict):
    upload(
        client,
        auth,
        "research.pdf",
        [
            "The solar system orbits a central star.",
            "Machine learning is a subset of artificial intelligence that learns from data.",
            "Cooking pasta requires salted boiling water.",
        ],
    )

    response = client.post(
        "/api/chat", headers=auth, json={"question": "What is machine learning?"}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["has_context"] is True
    assert body["answer"]
    assert body["sources"], "expected retrieved chunks to be cited"

    top = body["sources"][0]
    assert top["filename"] == "research.pdf"
    assert top["page"] == 2, "the ML sentence lives on page 2"
    assert "machine learning" in top["snippet"].lower()
    assert 0.0 <= top["score"] <= 1.0
    assert all(0.0 <= source["score"] <= 1.0 for source in body["sources"])
    assert all(
        source["score"] >= settings.min_relevance_score for source in body["sources"]
    ), "every cited source should have cleared the relevance floor"


def test_chat_ranks_the_matching_chunk_first(client: TestClient, auth: dict):
    upload(
        client,
        auth,
        "topics.pdf",
        [
            "Marine biology covers coral reefs and ocean life.",
            "Vector databases store embeddings for semantic search.",
            "Machine learning models learn patterns from training data.",
        ],
    )

    body = client.post(
        "/api/chat", headers=auth, json={"question": "machine learning models"}
    ).json()

    assert body["sources"][0]["page"] == 3


def test_chat_can_scope_to_selected_documents(client: TestClient, auth: dict):
    marine = upload(client, auth, "marine.pdf", ["Coral reefs host diverse marine life."])
    upload(client, auth, "cooking.pdf", ["Boil salted water to cook pasta."])

    body = client.post(
        "/api/chat",
        headers=auth,
        json={"question": "marine life", "document_ids": [marine["id"]]},
    ).json()

    assert {source["document_id"] for source in body["sources"]} == {marine["id"]}


def test_chat_history_records_both_turns(client: TestClient, auth: dict):
    upload(client, auth, "research.pdf", ["Machine learning basics."])
    client.post("/api/chat", headers=auth, json={"question": "What is machine learning?"})

    history = client.get("/api/chat/history", headers=auth).json()
    assert history["total"] == 2
    assert [message["role"] for message in history["messages"]] == ["user", "assistant"]
    assert history["messages"][1]["sources"]

    assert client.delete("/api/chat/history", headers=auth).status_code == 204
    assert client.get("/api/chat/history", headers=auth).json()["total"] == 0


def test_chat_without_matches_reports_no_context(
    client: TestClient, auth: dict, monkeypatch
):
    upload(client, auth, "research.pdf", ["Machine learning basics."])
    monkeypatch.setattr(
        "app.api.routes_chat.vector_store.similarity_search", lambda **_: []
    )

    body = client.post(
        "/api/chat", headers=auth, json={"question": "Unrelated question?"}
    ).json()

    assert body["has_context"] is False
    assert body["sources"] == []
    assert "could not find an answer" in body["answer"].lower()


def test_chat_reports_service_unavailable_when_embeddings_fail(
    client: TestClient, auth: dict, monkeypatch
):
    upload(client, auth, "research.pdf", ["Machine learning basics."])

    def explode(_text: str):
        raise RuntimeError("model weights missing")

    monkeypatch.setattr("app.api.routes_chat.embed_query", explode)

    response = client.post(
        "/api/chat", headers=auth, json={"question": "What is machine learning?"}
    )

    assert response.status_code == 503
    assert "could not be loaded" in response.json()["detail"]


def test_llm_prompt_contains_retrieved_context(client: TestClient, auth: dict, offline_models):
    upload(client, auth, "research.pdf", ["Machine learning learns patterns from data."])
    client.post("/api/chat", headers=auth, json={"question": "What is machine learning?"})

    prompt = offline_models.prompts[-1]
    assert "What is machine learning?" in prompt
    assert "research.pdf (page 1)" in prompt
    assert "ONLY the context" in prompt
