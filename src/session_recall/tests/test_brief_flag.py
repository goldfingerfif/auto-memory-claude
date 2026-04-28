"""Tests for --brief flag — scrubs summary fields under --json for cheap structured output."""
import io
import json
import os
import sqlite3
import tempfile
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from session_recall.util.format_output import _scrub_summaries, output


def test_scrub_summaries_drops_top_level_summary():
    data = {"id": "x", "summary": "long blob"}
    assert _scrub_summaries(data) == {"id": "x"}


def test_scrub_summaries_drops_session_summary():
    data = {"file_path": "a.py", "session_summary": "blob"}
    assert _scrub_summaries(data) == {"file_path": "a.py"}


def test_scrub_summaries_recurses_into_lists():
    data = {"sessions": [
        {"id": "1", "summary": "blob"},
        {"id": "2", "summary": "blob2"},
    ]}
    result = _scrub_summaries(data)
    assert result == {"sessions": [{"id": "1"}, {"id": "2"}]}


def test_scrub_summaries_handles_nested():
    data = {"a": {"b": {"summary": "blob", "c": "keep"}}}
    assert _scrub_summaries(data) == {"a": {"b": {"c": "keep"}}}


def test_scrub_summaries_leaves_other_keys():
    data = {"id": "x", "date": "2026-04-28", "summary": "blob"}
    result = _scrub_summaries(data)
    assert "id" in result
    assert "date" in result
    assert "summary" not in result


def test_output_brief_json_drops_summary():
    data = {"sessions": [{"id": "x", "summary": "long blob"}]}
    buf = io.StringIO()
    with redirect_stdout(buf):
        output(data, json_mode=True, brief=True)
    parsed = json.loads(buf.getvalue())
    assert "summary" not in parsed["sessions"][0]


def test_output_no_brief_json_keeps_summary():
    data = {"sessions": [{"id": "x", "summary": "long blob"}]}
    buf = io.StringIO()
    with redirect_stdout(buf):
        output(data, json_mode=True, brief=False)
    parsed = json.loads(buf.getvalue())
    assert parsed["sessions"][0]["summary"] == "long blob"


def test_output_brief_text_mode_is_noop():
    """Text mode is already terse — --brief should not strip summary that text formatter reads."""
    data = {"sessions": [
        {"id": "abc12345", "id_short": "abc12345", "summary": "blob",
         "date": "2026-04-28", "turns_count": 3}
    ]}
    buf_brief = io.StringIO()
    buf_normal = io.StringIO()
    with redirect_stdout(buf_brief):
        output(data, json_mode=False, brief=True)
    with redirect_stdout(buf_normal):
        output(data, json_mode=False, brief=False)
    assert buf_brief.getvalue() == buf_normal.getvalue()


def test_brief_substantially_smaller():
    """Sanity: --brief --json output bytes should be at least 30% smaller for typical data."""
    sessions = [
        {"id_short": f"sess{i:04d}", "id_full": f"sess{i:04d}-uuid",
         "summary": "A long session summary that takes up many bytes " * 5,
         "date": "2026-04-28", "turns_count": 10, "files_count": 3}
        for i in range(10)
    ]
    data = {"repo": "all", "count": 10, "sessions": sessions}
    buf_full = io.StringIO()
    buf_brief = io.StringIO()
    with redirect_stdout(buf_full):
        output(data, json_mode=True, brief=False)
    with redirect_stdout(buf_brief):
        output(data, json_mode=True, brief=True)
    full_size = len(buf_full.getvalue())
    brief_size = len(buf_brief.getvalue())
    assert brief_size < full_size * 0.7, \
        f"--brief should be <70% of full size, got {brief_size}/{full_size}"


def _make_test_db() -> str:
    """Copilot-shape DB matching schema_check expectations."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = f.name
    f.close()
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE sessions (
        id TEXT PRIMARY KEY, cwd TEXT, repository TEXT, branch TEXT,
        summary TEXT, created_at TEXT, updated_at TEXT, host_type TEXT)""")
    conn.execute("""CREATE TABLE turns (
        id INTEGER PRIMARY KEY, session_id TEXT, turn_index INTEGER,
        user_message TEXT, assistant_response TEXT, timestamp TEXT)""")
    conn.execute("""CREATE TABLE session_files (
        id INTEGER PRIMARY KEY, session_id TEXT, file_path TEXT,
        tool_name TEXT, turn_index INTEGER, first_seen_at TEXT)""")
    conn.execute("""CREATE TABLE session_refs (
        id INTEGER PRIMARY KEY, session_id TEXT, ref_type TEXT,
        ref_value TEXT, turn_index INTEGER, created_at TEXT)""")
    conn.execute("""CREATE TABLE checkpoints (
        id INTEGER PRIMARY KEY, session_id TEXT, checkpoint_number INTEGER,
        title TEXT, overview TEXT, created_at TEXT)""")
    conn.execute("""INSERT INTO sessions VALUES (
        'abc12345-uuid', '/cwd', 'owner/repo', 'main',
        'A long session summary that should be scrubbed under --brief',
        datetime('now'), datetime('now'), 'claude')""")
    conn.execute("""INSERT INTO session_files VALUES (
        1, 'abc12345-uuid', '/cwd/foo.py', 'Read', 0, datetime('now'))""")
    conn.commit()
    conn.close()
    return path


def test_list_command_brief_drops_summary():
    """End-to-end: list --json --brief excludes summary key."""
    path = _make_test_db()
    try:
        with patch("session_recall.commands.list_sessions.DB_PATH", path), \
             patch("session_recall.commands.list_sessions.detect_repo", return_value="owner/repo"):
            from session_recall.commands.list_sessions import run
            args = SimpleNamespace(repo="all", limit=10, days=30, json=True, brief=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                run(args)
            parsed = json.loads(buf.getvalue())
            assert parsed["count"] == 1
            assert "summary" not in parsed["sessions"][0]
    finally:
        os.unlink(path)


def test_list_command_no_brief_keeps_summary():
    path = _make_test_db()
    try:
        with patch("session_recall.commands.list_sessions.DB_PATH", path), \
             patch("session_recall.commands.list_sessions.detect_repo", return_value="owner/repo"):
            from session_recall.commands.list_sessions import run
            args = SimpleNamespace(repo="all", limit=10, days=30, json=True, brief=False)
            buf = io.StringIO()
            with redirect_stdout(buf):
                run(args)
            parsed = json.loads(buf.getvalue())
            assert "summary" in parsed["sessions"][0]
            assert "scrubbed under --brief" in parsed["sessions"][0]["summary"]
    finally:
        os.unlink(path)


def test_files_command_brief_drops_session_summary():
    """End-to-end: files --json --brief excludes session_summary key."""
    path = _make_test_db()
    try:
        with patch("session_recall.commands.files.DB_PATH", path), \
             patch("session_recall.commands.files.detect_repo", return_value="owner/repo"):
            from session_recall.commands.files import run
            args = SimpleNamespace(repo="all", limit=10, days=None, json=True, brief=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                run(args)
            parsed = json.loads(buf.getvalue())
            assert parsed["count"] >= 1
            for f in parsed["files"]:
                assert "session_summary" not in f
    finally:
        os.unlink(path)
