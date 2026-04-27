"""Dim 1: Freshness — how recently did the upstream agent write data."""
import os
import time
from ..config import DB_PATH
from .scoring import score_dim

HINT = "Use the agent (Copilot/Claude) — store only updates from active sessions"


def check(backend=None) -> dict:
    mtime = None
    if backend is not None and backend.freshness_signal is not None:
        try:
            mtime = backend.freshness_signal()
        except Exception:
            mtime = None
    if mtime is None:
        path = backend.db_path if backend is not None else DB_PATH
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return {"name": "Freshness", "score": 0, "zone": "RED",
                    "detail": "data store not found", "hint": HINT}
    age_hours = (time.time() - mtime) / 3600
    result = score_dim(age_hours, green_threshold=24, amber_threshold=72,
                       higher_is_better=False)
    result.update({"name": "Freshness", "detail": f"{age_hours:.1f}h old",
                   "hint": HINT})
    return result
