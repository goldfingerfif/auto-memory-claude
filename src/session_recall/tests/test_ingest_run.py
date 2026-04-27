"""Tests for ingest/run.py — the incremental driver that turns JSONL into SQLite."""
import shutil
import sqlite3
from pathlib import Path

from session_recall.ingest.run import run_incremental, index_state, newest_jsonl_mtime
from session_recall.db.schema_check import EXPECTED_SCHEMA, schema_check


FIXTURE = Path(__file__).parent / "fixtures" / "claude_session.jsonl"


def _setup_projects(tmp_path: Path) -> tuple[Path, Path]:
    """Create a fake projects/<encoded-cwd>/<sessionId>.jsonl tree."""
    projects = tmp_path / "projects"
    project_dir = projects / "C--home--u--proj"
    project_dir.mkdir(parents=True)
    dst = project_dir / "c335351c-cad3-4f99-902b-1d46e7807fbc.jsonl"
    shutil.copy(FIXTURE, dst)
    return projects, dst


def test_run_incremental_builds_full_index(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    summary = run_incremental(db_path=str(db), projects_dir=str(projects))
    assert summary["files_seen"] == 1
    assert summary["files_ingested"] == 1
    assert summary["errors"] == 0


def test_index_schema_matches_expected(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    run_incremental(db_path=str(db), projects_dir=str(projects))
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    problems = schema_check(conn, EXPECTED_SCHEMA)
    conn.close()
    assert problems == []


def test_session_row_populated(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    run_incremental(db_path=str(db), projects_dir=str(projects))
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, summary, branch, cwd, host_type FROM sessions").fetchall()
    conn.close()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "c335351c-cad3-4f99-902b-1d46e7807fbc"
    assert row["branch"] == "main"
    assert row["host_type"] == "claude-code"
    assert row["summary"].startswith("~")
    assert "auth" in row["summary"]


def test_turns_are_grouped(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    run_incremental(db_path=str(db), projects_dir=str(projects))
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT turn_index, user_message, assistant_response "
        "FROM turns WHERE session_id = ? ORDER BY turn_index",
        ("c335351c-cad3-4f99-902b-1d46e7807fbc",)
    ).fetchall()
    conn.close()
    # Two user messages → two turns
    assert len(rows) == 2
    assert "auth" in rows[0][1]
    assert "test" in rows[1][1].lower()


def test_file_touches_extracted(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    run_incremental(db_path=str(db), projects_dir=str(projects))
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT file_path, tool_name FROM session_files WHERE session_id = ?",
        ("c335351c-cad3-4f99-902b-1d46e7807fbc",)
    ).fetchall()
    conn.close()
    paths = {r[0] for r in rows}
    tools = {r[1] for r in rows}
    assert "/home/u/proj/auth/handler.py" in paths
    assert "/home/u/proj/tests/test_handler.py" in paths
    assert "Read" in tools
    assert "Write" in tools


def test_checkpoint_from_plan_mode(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    run_incremental(db_path=str(db), projects_dir=str(projects))
    conn = sqlite3.connect(str(db))
    cps = conn.execute(
        "SELECT checkpoint_number, title FROM checkpoints WHERE session_id = ?",
        ("c335351c-cad3-4f99-902b-1d46e7807fbc",)
    ).fetchall()
    conn.close()
    assert len(cps) == 1
    assert "auth" in cps[0][1].lower()


def test_search_index_populated(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    run_incremental(db_path=str(db), projects_dir=str(projects))
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT source_type FROM search_index WHERE session_id = ?",
        ("c335351c-cad3-4f99-902b-1d46e7807fbc",)
    ).fetchall()
    conn.close()
    types = {r[0] for r in rows}
    assert "user" in types
    assert "assistant" in types
    # Summary row also goes in
    assert "summary" in types


def test_idempotent_no_change(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    run_incremental(db_path=str(db), projects_dir=str(projects))
    summary2 = run_incremental(db_path=str(db), projects_dir=str(projects))
    assert summary2["files_skipped"] == 1
    assert summary2["files_ingested"] == 0


def test_full_rebuild_drops_and_reingests(tmp_path):
    projects, jsonl = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    run_incremental(db_path=str(db), projects_dir=str(projects))
    summary2 = run_incremental(db_path=str(db), projects_dir=str(projects), full=True)
    assert summary2["files_ingested"] == 1
    assert summary2["files_skipped"] == 0


def test_index_state_reports_after_ingest(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    db = tmp_path / "index.db"
    run_incremental(db_path=str(db), projects_dir=str(projects))
    st = index_state(str(db))
    assert st["exists"]
    assert st["files"] == 1
    assert st["last_ingested_at"]


def test_newest_jsonl_mtime(tmp_path):
    projects, _ = _setup_projects(tmp_path)
    m = newest_jsonl_mtime(str(projects))
    assert m is not None
    assert isinstance(m, float)


def test_empty_projects_dir_safe(tmp_path):
    projects = tmp_path / "projects"
    projects.mkdir()
    db = tmp_path / "index.db"
    summary = run_incremental(db_path=str(db), projects_dir=str(projects))
    assert summary["files_seen"] == 0
    assert summary["errors"] == 0


def test_missing_projects_dir_safe(tmp_path):
    db = tmp_path / "index.db"
    summary = run_incremental(db_path=str(db),
                              projects_dir=str(tmp_path / "nope"))
    assert summary["files_seen"] == 0
