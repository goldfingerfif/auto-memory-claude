"""Dim 5: Summary coverage — % of real sessions (≥1 turn) with non-null summary.

Note for the Claude Code backend: Claude doesn't write native summaries, so
the ingestor derives one from the first user message (prefixed with `~`). The
percentage is still meaningful (it measures parseable transcripts) but the
detail line annotates `(auto-derived)` so operators don't confuse it with a
Copilot-style native-summary signal.
"""
from ..db.connect import connect_ro
from ..config import DB_PATH
from .scoring import score_dim

HINT = "Summaries fill post-session; ghost sessions (0 turns) are excluded"


def check(backend=None) -> dict:
    db_path = backend.db_path if backend is not None else DB_PATH
    is_claude = backend is not None and backend.name == "claude"
    try:
        conn = connect_ro(db_path)
        total = conn.execute(
            "SELECT COUNT(*) FROM sessions s "
            "WHERE EXISTS (SELECT 1 FROM turns t WHERE t.session_id = s.id)"
        ).fetchone()[0]
        with_summary = conn.execute(
            "SELECT COUNT(*) FROM sessions s "
            "WHERE s.summary IS NOT NULL AND s.summary != '' "
            "AND EXISTS (SELECT 1 FROM turns t WHERE t.session_id = s.id)"
        ).fetchone()[0]
        ghosts = conn.execute(
            "SELECT COUNT(*) FROM sessions s "
            "WHERE NOT EXISTS (SELECT 1 FROM turns t WHERE t.session_id = s.id)"
        ).fetchone()[0]
        conn.close()
    except Exception as e:
        return {"name": "Summary Coverage", "score": 0, "zone": "RED",
                "detail": str(e), "hint": HINT}
    pct = (with_summary / total * 100) if total > 0 else 0
    result = score_dim(pct, green_threshold=80, amber_threshold=40)
    detail = f"{pct:.0f}% ({with_summary}/{total})"
    if is_claude:
        detail += " (auto-derived)"
    if ghosts:
        detail += f" — {ghosts} ghost sessions excluded"
    result.update({"name": "Summary Coverage", "detail": detail, "hint": HINT})
    return result
