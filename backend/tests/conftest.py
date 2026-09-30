import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Point every path-backed component at a throwaway directory *before* the
# application modules are imported, so tests never touch real user data.
_TMP_ROOT = Path(tempfile.mkdtemp(prefix="rag-tests-"))
os.environ.setdefault("UPLOAD_DIRECTORY", str(_TMP_ROOT / "documents"))
os.environ.setdefault("CHROMA_PERSIST_DIRECTORY", str(_TMP_ROOT / "chroma_db"))
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

ANSWER = "Machine learning is a subset of artificial intelligence."


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_root():
    yield
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def offline_models(monkeypatch):
    """Swap the sentence-transformer and Ollama models for deterministic fakes.

    Everything else in the pipeline (PyMuPDF extraction, chunking, ChromaDB
    storage and similarity search) still runs for real.
    """
    from tests.fakes import FakeEmbeddings, FakeLLM

    fake_embeddings = FakeEmbeddings()
    fake_llm = FakeLLM(ANSWER)

    monkeypatch.setattr("app.rag.embeddings.get_embeddings", lambda: fake_embeddings)
    monkeypatch.setattr("app.api.routes_chat.embed_query", fake_embeddings.embed_query)
    monkeypatch.setattr("app.rag.chain.get_llm", lambda: fake_llm)
    monkeypatch.setattr("app.rag.chain.llm_is_available", lambda: True)

    return fake_llm


@pytest.fixture
def credentials() -> dict[str, str]:
    return {
        "email": f"user-{uuid.uuid4().hex[:8]}@example.com",
        "password": "supersecret",
    }


@pytest.fixture
def auth(client, credentials: dict[str, str]) -> dict[str, str]:
    """A registered user with a bearer header, shared by the API tests."""
    response = client.post("/api/auth/register", json=credentials)
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def store():
    from app.services.user_service import UserStore

    return UserStore(path=_TMP_ROOT / f"users-{os.urandom(4).hex()}.json")


@pytest.fixture
def registry():
    from app.services.document_service import DocumentRegistry

    return DocumentRegistry()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
