"""Schema validation against expected session-store DB structure.

`EXPECTED_SCHEMA` is the Copilot CLI shape; the Claude Code backend mirrors
this exact shape in its index DB so this check is reusable across backends.
Pass `expected=` to validate against a different schema dict.
"""

EXPECTED_SCHEMA: dict[str, set[str]] = {
    "sessions": {"id", "repository", "branch", "summary", "created_at", "updated_at"},
    "turns": {"session_id", "turn_index", "user_message", "assistant_response", "timestamp"},
    "session_files": {"session_id", "file_path", "tool_name", "turn_index", "first_seen_at"},
    "session_refs": {"session_id", "ref_type", "ref_value", "turn_index", "created_at"},
    "checkpoints": {"session_id", "checkpoint_number", "title", "overview", "created_at"},
}


def schema_check(conn, expected: dict[str, set[str]] | None = None) -> list[str]:
    """Validate DB schema. Returns list of problems (empty = OK).

    `expected` defaults to EXPECTED_SCHEMA (Copilot/Claude-index shape).
    """
    if expected is None:
        expected = EXPECTED_SCHEMA
    problems: list[str] = []
    for table, expected_cols in expected.items():
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not rows:
            problems.append(f"MISSING TABLE: {table}")
            continue
        actual = {r[1] if isinstance(r, tuple) else r["name"] for r in rows}
        missing = expected_cols - actual
        if missing:
            problems.append(f"{table}: missing columns {missing}")
    return problems
