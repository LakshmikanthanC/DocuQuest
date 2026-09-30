"""In-session chat history, stored per user in memory."""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from datetime import datetime, timezone

from app.models.schemas import ChatMessage, ChartPublic, SourceCitation

MAX_HISTORY = 50

_lock = threading.RLock()
_history: dict[str, deque[ChatMessage]] = defaultdict(
    lambda: deque(maxlen=MAX_HISTORY)
)


def add_message(
    user_id: str,
    role: str,
    content: str,
    sources: list[SourceCitation] | None = None,
    chart: ChartPublic | None = None,
    diagram: str | None = None,
) -> ChatMessage:
    message = ChatMessage(
        role=role,  # type: ignore[arg-type]
        content=content,
        sources=sources or [],
        created_at=datetime.now(timezone.utc),
        chart=chart,
        diagram=diagram,
    )
    with _lock:
        _history[user_id].append(message)
    return message


def get_history(user_id: str) -> list[ChatMessage]:
    with _lock:
        return list(_history.get(user_id, ()))


def clear_history(user_id: str) -> None:
    with _lock:
        _history.pop(user_id, None)
