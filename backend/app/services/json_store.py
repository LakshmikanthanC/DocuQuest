"""Durable JSON-file reads and writes for the in-process stores.

Both the user store and the document registry keep their state in a single JSON
file. Two failure modes motivated this module:

1. A partially written file. ``Path.write_text`` truncates first, so a crash or
   a full disk mid-write leaves invalid JSON, and the next boot would discard
   every record. Writing to a temporary file in the same directory and then
   calling ``os.replace`` is atomic on POSIX and Windows, so readers see either
   the old file or the new one, never a half-written one.
2. Silent data loss. A corrupt file used to be treated as "no data yet", which
   quietly reset the store to empty. It is now renamed aside and logged at
   error level so the original bytes are still recoverable.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("rag.json_store")


def write_json_atomically(path: Path, payload: list[dict[str, Any]]) -> None:
    """Serialise ``payload`` to ``path`` as a complete file or not at all."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def read_json_list(path: Path, label: str) -> list[dict[str, Any]] | None:
    """Return the list stored at ``path``, or None when there is nothing to read.

    A malformed file is preserved next to the original as ``<name>.corrupt`` and
    reported, so the operator can inspect it instead of losing it silently.
    """
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _quarantine(path, label, "unreadable")
        return None
    if not isinstance(raw, list):
        _quarantine(path, label, "not a JSON array")
        return None
    return raw


def _quarantine(path: Path, label: str, reason: str) -> None:
    preserved = path.with_suffix(path.suffix + ".corrupt")
    try:
        os.replace(path, preserved)
    except OSError:
        logger.exception(
            "Could not preserve the corrupt %s file at %s; "
            "it is being left in place and will be ignored",
            label,
            path,
        )
        return
    logger.error(
        "The %s file at %s was %s and has been moved to %s. "
        "It will start empty; restore the backup to recover the records",
        label,
        path,
        reason,
        preserved,
    )
