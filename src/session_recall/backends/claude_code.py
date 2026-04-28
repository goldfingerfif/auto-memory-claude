"""Claude Code backend.

Reads ~/.claude/projects/**/*.jsonl, ingests into a Copilot-shaped SQLite
index at ~/.claude/.session-recall.db, then queries it read-only via the
existing command layer.

ensure_index() runs an incremental ingest on every CLI call; it's a near-no-op
when nothing on disk has changed.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import Backend
from ..db.schema_check import EXPECTED_SCHEMA
from ..ingest import run as ingest_run


DEFAULT_PROJECTS_DIR = str(Path.home() / ".claude" / "projects")
DEFAULT_INDEX_DB = str(Path.home() / ".claude" / ".session-recall.db")
DEFAULT_INSTRUCTIONS_PATH = str(Path.home() / ".claude" / "CLAUDE.md")


def build() -> Backend:
    db_path = os.environ.get("SESSION_RECALL_DB", DEFAULT_INDEX_DB)
    projects_dir = os.environ.get(
        "SESSION_RECALL_CLAUDE_PROJECTS", DEFAULT_PROJECTS_DIR
    )
    instructions = os.environ.get(
        "SESSION_RECALL_CLAUDE_INSTRUCTIONS", DEFAULT_INSTRUCTIONS_PATH
    )

    def ensure_index() -> None:
        if not Path(projects_dir).exists():
            return
        ingest_run.run_incremental(db_path=db_path, projects_dir=projects_dir,
                                   full=False, verbose=False)

    def freshness_signal():
        return ingest_run.newest_jsonl_mtime(projects_dir)

    return Backend(
        name="claude",
        db_path=db_path,
        instructions_path=instructions,
        expected_schema=EXPECTED_SCHEMA,
        ensure_index=ensure_index,
        freshness_signal=freshness_signal,
        # Claude Code sessions are long (50–100+ turns each); a small corpus
        # already represents thousands of recall-eligible turns. Tuned so a
        # week of regular use scores a clean 10 instead of perpetual 8/9.
        corpus_thresholds=(5, 2),
    )
