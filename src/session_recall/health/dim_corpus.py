"""Dim 4: Corpus size — number of sessions in DB."""
from ..db.connect import connect_ro
from ..config import DB_PATH
from .scoring import score_dim

HINT = "Cold start — will improve with usage"


def check(backend=None) -> dict:
    db_path = backend.db_path if backend is not None else DB_PATH
    try:
        conn = connect_ro(db_path)
        count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        conn.close()
    except Exception as e:
        return {"name": "Corpus Size", "score": 0, "zone": "RED",
                "detail": str(e), "hint": HINT}
    result = score_dim(count, green_threshold=50, amber_threshold=10)
    result.update({"name": "Corpus Size", "detail": f"{count} sessions", "hint": HINT})
    return result
