"""Dim 4: Corpus size — number of sessions in DB.

Thresholds come from `backend.corpus_thresholds` (a `(green, amber)` tuple)
when a backend is supplied; falls back to Copilot-style `(50, 10)` defaults
otherwise. Claude Code sessions are typically much longer than Copilot
sessions, so the Claude backend ships lower thresholds.
"""
from ..db.connect import connect_ro
from ..config import DB_PATH
from .scoring import score_dim

HINT = "Cold start — will improve with usage"
DEFAULT_THRESHOLDS = (50, 10)


def check(backend=None) -> dict:
    db_path = backend.db_path if backend is not None else DB_PATH
    green, amber = (backend.corpus_thresholds
                    if backend is not None
                    else DEFAULT_THRESHOLDS)
    try:
        conn = connect_ro(db_path)
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()
    except Exception as e:
        return {"name": "Corpus Size", "score": 0, "zone": "RED",
                "detail": str(e), "hint": HINT}
    result = score_dim(count, green_threshold=green, amber_threshold=amber)
    result.update({"name": "Corpus Size", "detail": f"{count} sessions",
                   "hint": HINT})
    return result
