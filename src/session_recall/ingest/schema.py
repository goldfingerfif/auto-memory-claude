"""SQLite schema for the Claude Code index.

Mirrors the Copilot CLI shape (see db/schema_check.EXPECTED_SCHEMA) so the
existing read-only command layer can query either backend identically.
Adds a single internal table — `_ingest_state` — to drive incremental ingest.
"""
from __future__ import annotations


SCHEMA_SQL = [
    """CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        repository TEXT,
        branch TEXT,
        summary TEXT,
        cwd TEXT,
        created_at TEXT,
        updated_at TEXT,
        host_type TEXT,
        jsonl_path TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS turns (
        session_id TEXT,
        turn_index INTEGER,
        user_message TEXT,
        assistant_response TEXT,
        timestamp TEXT,
        PRIMARY KEY (session_id, turn_index)
    )""",
    """CREATE TABLE IF NOT EXISTS session_files (
        session_id TEXT,
        file_path TEXT,
        tool_name TEXT,
        turn_index INTEGER,
        first_seen_at TEXT,
        PRIMARY KEY (session_id, file_path, tool_name)
    )""",
    """CREATE TABLE IF NOT EXISTS session_refs (
        session_id TEXT,
        ref_type TEXT,
        ref_value TEXT,
        turn_index INTEGER,
        created_at TEXT,
        PRIMARY KEY (session_id, ref_type, ref_value)
    )""",
    """CREATE TABLE IF NOT EXISTS checkpoints (
        session_id TEXT,
        checkpoint_number INTEGER,
        title TEXT,
        overview TEXT,
        created_at TEXT,
        PRIMARY KEY (session_id, checkpoint_number)
    )""",
    # Internal: track per-JSONL-file ingest state. Not validated by schema_check.
    """CREATE TABLE IF NOT EXISTS _ingest_state (
        jsonl_path TEXT PRIMARY KEY,
        session_id TEXT,
        mtime_ns INTEGER,
        byte_size INTEGER,
        last_line_count INTEGER,
        ingested_at TEXT
    )""",
    # FTS5 virtual table — search_index. Matches the query in commands/search.py.
    """CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
        content,
        session_id UNINDEXED,
        source_type UNINDEXED,
        tokenize='unicode61'
    )""",
    # Helpful indexes
    """CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC)""",
    """CREATE INDEX IF NOT EXISTS idx_sessions_repository ON sessions(repository)""",
    """CREATE INDEX IF NOT EXISTS idx_files_first_seen ON session_files(first_seen_at DESC)""",
    """CREATE INDEX IF NOT EXISTS idx_checkpoints_created ON checkpoints(created_at DESC)""",
]


def apply_schema(conn) -> None:
    """Execute every CREATE statement; safe to call repeatedly."""
    for stmt in SCHEMA_SQL:
        conn.execute(stmt)
