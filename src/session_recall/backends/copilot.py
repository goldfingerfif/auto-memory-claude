"""GitHub Copilot CLI backend — reads ~/.copilot/session-store.db directly.

Copilot CLI maintains its own SQLite store with FTS5; we just point at it
read-only. ensure_index() is a no-op since the upstream tool maintains the DB.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import Backend
from ..db.schema_check import EXPECTED_SCHEMA


DEFAULT_DB_PATH = str(Path.home() / ".copilot" / "session-store.db")
DEFAULT_INSTRUCTIONS_PATH = str(Path.home() / ".copilot" / "copilot-instructions.md")


def build() -> Backend:
    db_path = os.environ.get("SESSION_RECALL_DB", DEFAULT_DB_PATH)
    instructions = os.environ.get(
        "SESSION_RECALL_COPILOT_INSTRUCTIONS", DEFAULT_INSTRUCTIONS_PATH
    )
    return Backend(
        name="copilot",
        db_path=db_path,
        instructions_path=instructions,
        expected_schema=EXPECTED_SCHEMA,
        ensure_index=lambda: None,
    )
