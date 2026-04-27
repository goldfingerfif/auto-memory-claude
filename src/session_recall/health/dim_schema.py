"""Dim 2: Schema integrity — expected tables and columns present."""
from ..db.connect import connect_ro
from ..db.schema_check import schema_check
from ..config import DB_PATH

HINT = "Run `session-recall schema-check` for details"


def check(backend=None) -> dict:
    db_path = backend.db_path if backend is not None else DB_PATH
    expected = backend.expected_schema if backend is not None else None
    try:
        conn = connect_ro(db_path)
        problems = schema_check(conn, expected)
        conn.close()
    except SystemExit:
        return {"name": "Schema Integrity", "score": 0, "zone": "RED",
                "detail": "DB connection failed", "hint": HINT}
    if not problems:
        return {"name": "Schema Integrity", "score": 10, "zone": "GREEN",
                "detail": "All tables/columns OK", "hint": ""}
    has_missing_table = any("MISSING TABLE" in p for p in problems)
    if has_missing_table:
        return {"name": "Schema Integrity", "score": 1, "zone": "RED",
                "detail": "; ".join(problems), "hint": HINT}
    return {"name": "Schema Integrity", "score": 5, "zone": "AMBER",
            "detail": "; ".join(problems), "hint": HINT}
