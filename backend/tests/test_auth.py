"""Auth, user-store, and security primitive tests."""

from __future__ import annotations

import time

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("correct horse battery")
    second = hash_password("correct horse battery")

    assert first != second, "bcrypt salt should make hashes differ"
    assert verify_password("correct horse battery", first)
    assert not verify_password("wrong password", first)


def test_verify_password_handles_malformed_hash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_jwt_round_trip_carries_subject():
    token = create_access_token("user-123", {"email": "a@b.com"})
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["email"] == "a@b.com"


def test_decode_rejects_token_signed_with_other_key():
    forged = jwt.encode({"sub": "1"}, "another-secret", algorithm=settings.jwt_algorithm)
    assert decode_access_token(forged) is None


def test_decode_rejects_expired_token():
    expired = jwt.encode(
        {"sub": "1", "exp": int(time.time()) - 60},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(expired) is None


def test_decode_rejects_garbage():
    assert decode_access_token("not.a.jwt") is None


# ---------------------------------------------------------------------------
# UserStore
# ---------------------------------------------------------------------------
def test_create_user_normalizes_email_and_hides_password(store):
    user = store.create("  Person@Example.COM ", "supersecret", " Person ")

    assert user.email == "person@example.com"
    assert user.full_name == "Person"
    public = user.public()
    assert "password_hash" not in public
    assert public["id"] == user.id


def test_create_duplicate_email_raises(store):
    store.create("dup@example.com", "supersecret", None)
    with pytest.raises(ValueError, match="already exists"):
        store.create("dup@example.com", "supersecret", None)


def test_authenticate_returns_user_only_for_right_password(store):
    store.create("auth@example.com", "supersecret", None)

    assert store.authenticate("auth@example.com", "supersecret") is not None
    assert store.authenticate("auth@example.com", "nope") is None
    assert store.authenticate("missing@example.com", "supersecret") is None


def test_user_store_persists_across_instances(tmp_path):
    from app.services.user_service import UserStore

    path = tmp_path / "users.json"
    first = UserStore(path=path)
    first.create("persist@example.com", "supersecret", None)

    second = UserStore(path=path)
    assert second.exists("persist@example.com")
    assert second.count() == 1


# ---------------------------------------------------------------------------
# Default account seeding
# ---------------------------------------------------------------------------
def test_ensure_default_user_creates_configured_account(store, monkeypatch):
    from app.services.user_service import ensure_default_user

    monkeypatch.setattr(settings, "seed_default_user", True)
    monkeypatch.setattr(settings, "default_user_email", "seed@example.com")
    monkeypatch.setattr(settings, "default_user_password", "seeded-password")
    monkeypatch.setattr(settings, "default_user_name", "Seeded Admin")

    seeded = ensure_default_user(store)

    assert seeded is not None
    assert store.authenticate("seed@example.com", "seeded-password") is not None
    assert store.get_by_email("seed@example.com").full_name == "Seeded Admin"


def test_ensure_default_user_is_idempotent(store, monkeypatch):
    from app.services.user_service import ensure_default_user

    monkeypatch.setattr(settings, "seed_default_user", True)
    monkeypatch.setattr(settings, "default_user_email", "seed@example.com")
    monkeypatch.setattr(settings, "default_user_password", "seeded-password")

    assert ensure_default_user(store) is not None
    assert ensure_default_user(store) is None
    assert store.count() == 1


def test_ensure_default_user_respects_opt_out(store, monkeypatch):
    from app.services.user_service import ensure_default_user

    monkeypatch.setattr(settings, "seed_default_user", False)

    assert ensure_default_user(store) is None
    assert store.count() == 0


def test_default_account_can_log_in(client):
    response = client.post(
        "/api/auth/login",
        json={"email": settings.default_user_email, "password": settings.default_user_password},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == settings.default_user_email
