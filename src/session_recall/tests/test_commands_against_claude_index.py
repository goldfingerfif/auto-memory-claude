"""Cross-backend integration test — every read command works against the
index built from JSONL fixtures.
"""
import json
import shutil
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from session_recall.backends import Backend
from session_recall.db.schema_check import EXPECTED_SCHEMA
from session_recall.ingest.run import run_incremental


FIXTURE = Path(__file__).parent / "fixtures" / "claude_session.jsonl"


def _build_index(tmp_path: Path) -> Backend:
    projects = tmp_path / "projects"
    project_dir = projects / "C--home--u--proj"
    project_dir.mkdir(parents=True)
    shutil.copy(FIXTURE, project_dir / "c335351c-cad3-4f99-902b-1d46e7807fbc.jsonl")
    db_path = tmp_path / "index.db"
    run_incremental(db_path=str(db_path), projects_dir=str(projects))
    return Backend(name="claude", db_path=str(db_path),
                   instructions_path="", expected_schema=EXPECTED_SCHEMA)


def _capture(fn, args, backend):
    """Run a command's run() with stdout captured; return (exit_code, parsed_json)."""
    buf = StringIO()
    with patch("sys.stdout", buf):
        code = fn(args, backend)
    text = buf.getvalue()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"_raw": text}
    return code, data


def test_list_against_claude_index(tmp_path):
    backend = _build_index(tmp_path)
    from session_recall.commands.list_sessions import run
    args = SimpleNamespace(repo="all", limit=10, days=30, json=True)
    code, data = _capture(run, args, backend)
    assert code == 0
    assert data["count"] == 1
    assert data["sessions"][0]["id_full"] == "c335351c-cad3-4f99-902b-1d46e7807fbc"


def test_files_against_claude_index(tmp_path):
    backend = _build_index(tmp_path)
    from session_recall.commands.files import run
    args = SimpleNamespace(repo="all", limit=10, days=None, json=True)
    code, data = _capture(run, args, backend)
    assert code == 0
    paths = {f["file_path"] for f in data["files"]}
    assert "/home/u/proj/auth/handler.py" in paths


def test_search_against_claude_index(tmp_path):
    backend = _build_index(tmp_path)
    from session_recall.commands.search import run
    args = SimpleNamespace(query="auth", repo="all", limit=10, days=None, json=True)
    code, data = _capture(run, args, backend)
    assert code == 0
    assert data["count"] >= 1


def test_show_against_claude_index(tmp_path):
    backend = _build_index(tmp_path)
    from session_recall.commands.show_session import run
    args = SimpleNamespace(session_id="c335351c", json=True, turns=None, full=False)
    code, data = _capture(run, args, backend)
    assert code == 0
    assert data["id"] == "c335351c-cad3-4f99-902b-1d46e7807fbc"
    assert data["turns_count"] == 2
    assert len(data["files"]) >= 2


def test_checkpoints_against_claude_index(tmp_path):
    backend = _build_index(tmp_path)
    from session_recall.commands.checkpoints import run
    args = SimpleNamespace(repo="all", limit=10, days=None, json=True)
    code, data = _capture(run, args, backend)
    assert code == 0
    assert data["count"] == 1


def test_schema_check_against_claude_index(tmp_path):
    backend = _build_index(tmp_path)
    from session_recall.commands.schema_check_cmd import run
    args = SimpleNamespace(json=True)
    code, data = _capture(run, args, backend)
    assert code == 0
    assert data.get("ok") is True
