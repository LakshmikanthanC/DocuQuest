"""JSON-file user store.

The brief lists PostgreSQL as *optional*; this keeps the app runnable with zero
external services. Swap this module for SQLAlchemy to persist users in Postgres.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.services.json_store import read_json_list, write_json_atomically


@dataclass(slots=True)
class User:
    id: str
    email: str
    password_hash: str
    full_name: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("password_hash")
        return data


class UserStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (settings.upload_directory / ".users.json")
        self._lock = threading.RLock()
        self._users: dict[str, User] = {}
        self._load()

    # -- persistence -------------------------------------------------------
    def _load(self) -> None:
        loaded = read_json_list(self._path, "user")
        if loaded is None:
            return
        self._users = {entry["email"]: User(**entry) for entry in loaded}

    def _flush(self) -> None:
        write_json_atomically(self._path, [asdict(user) for user in self._users.values()])

    # -- queries -----------------------------------------------------------
    def count(self) -> int:
        with self._lock:
            return len(self._users)

    def get_by_email(self, email: str) -> User | None:
        with self._lock:
            return self._users.get(email.strip().lower())

    def get_by_id(self, user_id: str) -> User | None:
        with self._lock:
            return next(
                (user for user in self._users.values() if user.id == user_id), None
            )

    def exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    # -- mutations ---------------------------------------------------------
    def create(self, email: str, password: str, full_name: str | None) -> User:
        with self._lock:
            normalized = email.strip().lower()
            if normalized in self._users:
                raise ValueError("User already exists")
            user = User(
                id=uuid.uuid4().hex,
                email=normalized,
                password_hash=hash_password(password),
                full_name=(full_name or "").strip() or None,
            )
            self._users[normalized] = user
            self._flush()
            return user

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.get_by_email(email)
        if user is None:
            return None
        return user if verify_password(password, user.password_hash) else None


_store: UserStore | None = None
_store_lock = threading.Lock()


def get_user_store() -> UserStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = UserStore()
        return _store


def ensure_default_user(store: UserStore | None = None) -> User | None:
    """Create the configured default account if it is missing.

    Idempotent: an existing account is left untouched so a changed password
    survives restarts. Returns the seeded user, or None when seeding is off or
    the account already exists.
    """

    if not settings.seed_default_user:
        return None
    target = store or get_user_store()
    if target.exists(settings.default_user_email):
        return None
    return target.create(
        settings.default_user_email,
        settings.default_user_password,
        settings.default_user_name,
    )
