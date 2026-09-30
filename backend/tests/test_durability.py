"""Durable JSON reads/writes, CORS configuration, and the relevance floor."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.services.json_store import read_json_list, write_json_atomically

# ---------------------------------------------------------------------------
# Atomic writes
# ---------------------------------------------------------------------------
def test_write_json_atomically_creates_parents_and_valid_json(tmp_path: Path):
    target = tmp_path / "nested" / "deeper" / "users.json"

    write_json_atomically(target, [{"email": "a@example.com"}])

    assert json.loads(target.read_text(encoding="utf-8")) == [{"email": "a@example.com"}]


def test_write_json_atomically_leaves_no_temp_files_behind(tmp_path: Path):
    target = tmp_path / "users.json"

    write_json_atomically(target, [{"email": "a@example.com"}])
    write_json_atomically(target, [{"email": "b@example.com"}])

    assert sorted(p.name for p in tmp_path.iterdir()) == ["users.json"]
    assert json.loads(target.read_text(encoding="utf-8")) == [{"email": "b@example.com"}]


def test_a_failed_write_keeps_the_previous_file_intact(tmp_path: Path):
    target = tmp_path / "users.json"
    write_json_atomically(target, [{"email": "kept@example.com"}])

    class Unserialisable:
        pass

    with pytest.raises(TypeError):
        write_json_atomically(target, [{"email": Unserialisable()}])

    assert json.loads(target.read_text(encoding="utf-8")) == [
        {"email": "kept@example.com"}
    ]
    assert list(tmp_path.iterdir()) == [target]


def test_read_json_list_returns_none_when_absent(tmp_path: Path):
    assert read_json_list(tmp_path / "missing.json", "user") is None


def test_unreadable_file_is_preserved_not_silently_dropped(tmp_path: Path):
    corrupt = tmp_path / "users.json"
    corrupt.write_text("{not json at all", encoding="utf-8")

    assert read_json_list(corrupt, "user") is None

    preserved = tmp_path / "users.json.corrupt"
    assert preserved.read_text(encoding="utf-8") == "{not json at all"
    assert not corrupt.exists(), "the original should be moved aside, not left in place"


def test_non_array_json_is_treated_as_corrupt(tmp_path: Path):
    target = tmp_path / "users.json"
    target.write_text('{"email": "a@example.com"}', encoding="utf-8")

    assert read_json_list(target, "user") is None
    assert (tmp_path / "users.json.corrupt").exists()


# ---------------------------------------------------------------------------
# Store integration
# ---------------------------------------------------------------------------
def test_user_store_survives_a_corrupt_file_on_reload(tmp_path: Path):
    from app.services.user_service import UserStore

    path = tmp_path / "users.json"
    store = UserStore(path=path)
    store.create("real@example.com", "supersecret", "Real")
    assert store.exists("real@example.com")

    path.write_text("{{{ truncated", encoding="utf-8")
    reloaded = UserStore(path=path)

    assert not reloaded.exists("real@example.com")
    assert (tmp_path / "users.json.corrupt").exists(), "original bytes must be kept"

    reloaded.create("next@example.com", "supersecret", "Next")
    assert reloaded.exists("next@example.com")
    assert UserStore(path=path).exists("next@example.com"), "new write must persist"


def test_document_registry_recovers_from_a_corrupt_file(tmp_path: Path, monkeypatch):
    from app.services import document_service
    from app.services.document_service import DocumentRecord, DocumentRegistry

    monkeypatch.setattr(
        document_service.settings, "upload_directory", tmp_path, raising=False
    )
    index = tmp_path / "documents.json"
    index.write_text("garbage", encoding="utf-8")

    registry = DocumentRegistry()
    assert registry.list_for_user("nobody") == []

    registry.add(
        DocumentRecord(
            id=uuid.uuid4().hex,
            user_id="u1",
            filename="a.pdf",
            stored_name="s.pdf",
            size_bytes=1,
            page_count=1,
            chunk_count=1,
        )
    )
    assert len(DocumentRegistry().list_for_user("u1")) == 1
    assert (tmp_path / "documents.json.corrupt").exists()


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
def test_cors_origins_default_to_local_dev_servers():
    assert Settings().cors_origin_list == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_cors_origins_are_parsed_from_a_comma_separated_string():
    parsed = Settings(
        cors_origins="https://app.example.com, https://www.example.com/"
    ).cors_origin_list
    assert parsed == ["https://app.example.com", "https://www.example.com"]


def test_cors_origins_dedupe_and_drop_blanks():
    parsed = Settings(
        cors_origins="http://a.test, ,http://a.test/ ,http://b.test"
    ).cors_origin_list
    assert parsed == ["http://a.test", "http://b.test"]


def test_wildcard_is_dropped_because_credentials_require_a_literal_origin():
    assert Settings(cors_origins="*,http://localhost:3000").cors_origin_list == [
        "http://localhost:3000"
    ]
    assert Settings(cors_origins="*").cors_origin_list == []


def test_configured_origin_is_allowed_and_others_are_not(client: TestClient):
    from app.core.config import settings

    allowed = settings.cors_origin_list[0]
    allowed_preflight = client.options(
        "/api/health",
        headers={
            "Origin": allowed,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed_preflight.headers.get("access-control-allow-origin") == allowed

    rejected = client.options(
        "/api/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in rejected.headers


def test_cors_origins_endpoint_reports_the_configured_list(client: TestClient):
    from app.core.config import settings

    response = client.get("/api/cors-origins")
    assert response.status_code == 200
    assert response.json()["origins"] == settings.cors_origin_list
