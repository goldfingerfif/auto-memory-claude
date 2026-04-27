"""Incremental ingest driver: walk ~/.claude/projects/**/*.jsonl, populate the
SQLite index. Idempotent — only re-touches files whose mtime or size changed
since the last run.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Iterable

from .schema import apply_schema
from .jsonl_reader import iter_lines
from .session_builder import build, SessionRows
from ..util.detect_repo import detect_repo


DEFAULT_PROJECTS_DIR = str(Path.home() / ".claude" / "projects")
DEFAULT_INDEX_DB = str(Path.home() / ".claude" / ".session-recall.db")


def _open_writer(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=2.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 1000")
    conn.execute("PRAGMA foreign_keys = OFF")
    apply_schema(conn)
    return conn


def _iter_jsonl_files(projects_dir: str) -> Iterable[Path]:
    root = Path(projects_dir)
    if not root.exists():
        return
    for project_dir in sorted(root.iterdir()):
        if not project_dir.is_dir():
            continue
        for jsonl in sorted(project_dir.glob("*.jsonl")):
            yield jsonl


def _full_rebuild_for_session(conn: sqlite3.Connection, session_id: str) -> None:
    """Wipe rows for one session_id from every backend-validated table."""
    if not session_id:
        return
    for table in ("turns", "session_files", "session_refs", "checkpoints"):
        conn.execute(f"DELETE FROM {table} WHERE session_id = ?", (session_id,))
    conn.execute(
        "DELETE FROM search_index WHERE session_id = ?", (session_id,)
    )
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def _persist(conn: sqlite3.Connection, jsonl_path: str, mtime_ns: int,
             byte_size: int, rows: SessionRows) -> None:
    if not rows.session_id:
        return
    sid = rows.session_id
    repository = detect_repo(cwd=rows.cwd) if rows.cwd else None
    if not repository and rows.cwd:
        repository = Path(rows.cwd).name  # last-segment fallback

    conn.execute(
        """INSERT OR REPLACE INTO sessions
           (id, repository, branch, summary, cwd, created_at, updated_at, host_type, jsonl_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sid, repository, rows.branch, rows.summary, rows.cwd,
         rows.created_at, rows.updated_at, "claude-code", jsonl_path),
    )
    # Replace turns / files / refs / checkpoints for this session in one go
    conn.execute("DELETE FROM turns WHERE session_id = ?", (sid,))
    conn.executemany(
        "INSERT INTO turns (session_id, turn_index, user_message, assistant_response, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        [(sid, t["turn_index"], t["user_message"], t["assistant_response"], t["timestamp"])
         for t in rows.turns],
    )
    conn.execute("DELETE FROM session_files WHERE session_id = ?", (sid,))
    conn.executemany(
        "INSERT OR IGNORE INTO session_files "
        "(session_id, file_path, tool_name, turn_index, first_seen_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [(sid, f["file_path"], f["tool_name"], f["turn_index"], f["first_seen_at"])
         for f in rows.files],
    )
    conn.execute("DELETE FROM checkpoints WHERE session_id = ?", (sid,))
    conn.executemany(
        "INSERT INTO checkpoints "
        "(session_id, checkpoint_number, title, overview, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [(sid, c["checkpoint_number"], c["title"], c["overview"], c["created_at"])
         for c in rows.checkpoints],
    )
    # FTS5: replace search_index rows for this session
    conn.execute("DELETE FROM search_index WHERE session_id = ?", (sid,))
    fts_rows: list[tuple[str, str, str]] = []
    if rows.summary:
        fts_rows.append((rows.summary, sid, "summary"))
    for t in rows.turns:
        if t["user_message"]:
            fts_rows.append((t["user_message"], sid, "user"))
        if t["assistant_response"]:
            fts_rows.append((t["assistant_response"], sid, "assistant"))
    conn.executemany(
        "INSERT INTO search_index (content, session_id, source_type) VALUES (?, ?, ?)",
        fts_rows,
    )
    # Update ingest checkpoint
    conn.execute(
        """INSERT OR REPLACE INTO _ingest_state
           (jsonl_path, session_id, mtime_ns, byte_size, last_line_count, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (jsonl_path, sid, mtime_ns, byte_size, rows.last_line,
         time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
    )


def run_incremental(db_path: str = DEFAULT_INDEX_DB,
                    projects_dir: str = DEFAULT_PROJECTS_DIR,
                    full: bool = False,
                    verbose: bool = False) -> dict:
    """Bring the index in sync with disk.

    Returns a dict summary: files_seen, files_ingested, files_skipped, sessions_touched.
    """
    summary = {"files_seen": 0, "files_ingested": 0, "files_skipped": 0,
               "sessions_touched": 0, "errors": 0}
    conn = _open_writer(db_path)
    try:
        if full:
            # Truth table for full rebuild: drop all rows but keep the schema.
            for table in ("sessions", "turns", "session_files", "session_refs",
                          "checkpoints", "_ingest_state"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute("DELETE FROM search_index")

        for jsonl in _iter_jsonl_files(projects_dir):
            summary["files_seen"] += 1
            try:
                st = jsonl.stat()
            except OSError:
                summary["errors"] += 1
                continue
            row = conn.execute(
                "SELECT mtime_ns, byte_size, last_line_count, session_id "
                "FROM _ingest_state WHERE jsonl_path = ?", (str(jsonl),)
            ).fetchone()

            mtime_ns = int(st.st_mtime_ns)
            size = int(st.st_size)

            # Decide: skip / append-only / full re-ingest
            if row and row["mtime_ns"] == mtime_ns and row["byte_size"] == size:
                summary["files_skipped"] += 1
                continue

            grew = bool(row and size >= row["byte_size"] and mtime_ns >= row["mtime_ns"])
            start_line = row["last_line_count"] if (row and grew) else 0

            # Load prior state if appending
            existing_rows: SessionRows | None = None
            if grew and row and row["session_id"]:
                existing_rows = _load_existing_rows(conn, row["session_id"], start_line)
            elif row and row["session_id"]:
                # Wipe and re-do this session
                _full_rebuild_for_session(conn, row["session_id"])

            try:
                rows = build(iter_lines(jsonl, start_line=start_line),
                             existing=existing_rows)
            except Exception as e:
                summary["errors"] += 1
                if verbose:
                    print(f"error parsing {jsonl}: {e}")
                continue

            if not rows.session_id:
                # Best-effort fallback: use the filename stem as the session id
                rows.session_id = jsonl.stem

            with conn:  # transaction
                _persist(conn, str(jsonl), mtime_ns, size, rows)
            summary["files_ingested"] += 1
            summary["sessions_touched"] += 1
            if verbose:
                print(f"ingested {jsonl.name} session={rows.session_id[:8]} "
                      f"turns={len(rows.turns)} files={len(rows.files)}")
        return summary
    finally:
        conn.close()


def _load_existing_rows(conn: sqlite3.Connection, session_id: str,
                        start_line: int) -> SessionRows:
    """Reconstruct a partial SessionRows from the index for incremental append."""
    rows = SessionRows(session_id=session_id, last_line=start_line)
    s = conn.execute(
        "SELECT repository, branch, summary, cwd, created_at, updated_at "
        "FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if s:
        rows.cwd = s["cwd"] or ""
        rows.branch = s["branch"] or ""
        rows.summary = s["summary"] or ""
        rows.created_at = s["created_at"] or ""
        rows.updated_at = s["updated_at"] or ""
        rows.summary_is_native = bool(rows.summary and not rows.summary.startswith("~"))
    rows.turns = [dict(r, _open=False) for r in conn.execute(
        "SELECT turn_index, user_message, assistant_response, timestamp "
        "FROM turns WHERE session_id = ? ORDER BY turn_index", (session_id,))]
    if rows.turns:
        rows.turns[-1]["_open"] = True
    rows.files = [dict(r) for r in conn.execute(
        "SELECT file_path, tool_name, turn_index, first_seen_at "
        "FROM session_files WHERE session_id = ?", (session_id,))]
    rows.checkpoints = [dict(r) for r in conn.execute(
        "SELECT checkpoint_number, title, overview, created_at "
        "FROM checkpoints WHERE session_id = ? ORDER BY checkpoint_number",
        (session_id,))]
    return rows


def newest_jsonl_mtime(projects_dir: str = DEFAULT_PROJECTS_DIR) -> float | None:
    """Return the unix mtime of the most recently modified JSONL, or None."""
    newest: float | None = None
    for jsonl in _iter_jsonl_files(projects_dir):
        try:
            m = jsonl.stat().st_mtime
        except OSError:
            continue
        if newest is None or m > newest:
            newest = m
    return newest


def index_state(db_path: str = DEFAULT_INDEX_DB) -> dict:
    """Return last-ingest summary from _ingest_state. Used by dim_ingest."""
    if not Path(db_path).exists():
        return {"exists": False, "files": 0, "last_ingested_at": None,
                "newest_mtime_ns": None}
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=0.5)
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError:
        return {"exists": False, "files": 0, "last_ingested_at": None,
                "newest_mtime_ns": None}
    try:
        row = conn.execute(
            "SELECT COUNT(*) as n, MAX(ingested_at) as last_at, MAX(mtime_ns) as newest "
            "FROM _ingest_state"
        ).fetchone()
        return {"exists": True, "files": row["n"] or 0,
                "last_ingested_at": row["last_at"],
                "newest_mtime_ns": row["newest"]}
    except sqlite3.OperationalError:
        return {"exists": False, "files": 0, "last_ingested_at": None,
                "newest_mtime_ns": None}
    finally:
        conn.close()
