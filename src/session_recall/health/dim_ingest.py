"""Dim 10: Index ingest health (Claude Code only).

Compares the newest JSONL mtime under ~/.claude/projects/ against the most
recent _ingest_state row in the index DB. If the index is more than a few
minutes behind disk, the user might be running session-recall against stale
data — recall will be missing the latest session.

For Copilot this dimension reports zone=N/A, score=None — `health/scoring.py`
already skips None-scored dims when computing the overall score.
"""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from .scoring import score_dim
from ..ingest.run import index_state, newest_jsonl_mtime
from ..backends.claude_code import DEFAULT_PROJECTS_DIR


def _parse_iso(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").timestamp()
    except (ValueError, TypeError):
        return None


def check(backend=None) -> dict:
    name = "Index Ingest"
    if backend is None or backend.name != "claude":
        return {"name": name, "score": None, "zone": "N/A",
                "detail": "Claude-only", "hint": ""}

    import os
    projects_dir = os.environ.get("SESSION_RECALL_CLAUDE_PROJECTS",
                                  DEFAULT_PROJECTS_DIR)
    if not Path(projects_dir).exists():
        return {"name": name, "score": None, "zone": "N/A",
                "detail": "no Claude projects dir", "hint": ""}

    state = index_state(backend.db_path)
    if not state["exists"] or state["files"] == 0:
        return {"name": name, "score": 1, "zone": "RED",
                "detail": "index empty — run `session-recall ingest`",
                "hint": "Run `session-recall ingest` to build the index"}

    newest_disk = newest_jsonl_mtime(projects_dir)
    last_ingest = _parse_iso(state["last_ingested_at"])
    now = time.time()

    if newest_disk is None:
        return {"name": name, "score": 5, "zone": "AMBER",
                "detail": "no JSONL files found", "hint": ""}

    # Lag = how far behind disk the index is, in minutes
    if last_ingest is None:
        lag_min = (now - newest_disk) / 60
    else:
        lag_min = max(0, (newest_disk - last_ingest)) / 60

    result = score_dim(lag_min, green_threshold=5, amber_threshold=60,
                       higher_is_better=False)
    detail = (f"{state['files']} files indexed, "
              f"{lag_min:.1f}m behind newest JSONL")
    result.update({"name": name, "detail": detail,
                   "hint": "Run `session-recall ingest` to refresh"})
    return result
