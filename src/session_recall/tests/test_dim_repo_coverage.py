"""Tests for health/dim_repo_coverage.py — three-step waterfall."""
import sqlite3
from unittest.mock import patch

from session_recall.backends import Backend
from session_recall.db.schema_check import EXPECTED_SCHEMA
from session_recall.health import dim_repo_coverage


def _build_index(tmp_path, sessions: list[dict]) -> Backend:
    db = tmp_path / "x.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE sessions (id TEXT, repository TEXT, cwd TEXT, "
        "branch TEXT, summary TEXT, created_at TEXT, updated_at TEXT)"
    )
    for s in sessions:
        conn.execute(
            "INSERT INTO sessions(id, repository, cwd) VALUES (?, ?, ?)",
            (s.get("id", "x"), s.get("repository"), s.get("cwd")),
        )
    conn.commit()
    conn.close()
    return Backend(name="claude", db_path=str(db), instructions_path="",
                   expected_schema=EXPECTED_SCHEMA)


def test_step1_git_remote_match(tmp_path):
    backend = _build_index(tmp_path, [
        {"id": "a", "repository": "owner/repo", "cwd": "/somewhere"},
    ])
    with patch("session_recall.health.dim_repo_coverage.detect_repo",
               return_value="owner/repo"):
        result = dim_repo_coverage.check(backend=backend)
    assert result["zone"] == "GREEN"
    assert "owner/repo" in result["detail"]


def test_step2_cwd_basename_match(tmp_path):
    """Git remote returns None, but `repository` column has the basename."""
    backend = _build_index(tmp_path, [
        {"id": "a", "repository": "auto-memory-main",
         "cwd": "/home/u/auto-memory-main"},
    ])
    with patch("session_recall.health.dim_repo_coverage.detect_repo",
               return_value=None), \
         patch("session_recall.health.dim_repo_coverage.os.getcwd",
               return_value="/home/u/auto-memory-main"):
        result = dim_repo_coverage.check(backend=backend)
    assert result["zone"] == "GREEN"
    assert "cwd:auto-memory-main" in result["detail"]


def test_step3_cwd_path_match(tmp_path):
    """No git remote, `repository` doesn't match basename, but cwd does."""
    backend = _build_index(tmp_path, [
        {"id": "a", "repository": "different-name",
         "cwd": "/home/u/myproj/src"},
    ])
    with patch("session_recall.health.dim_repo_coverage.detect_repo",
               return_value=None), \
         patch("session_recall.health.dim_repo_coverage.os.getcwd",
               return_value="/home/u/myproj"):
        result = dim_repo_coverage.check(backend=backend)
    # cwd LIKE '/home/u/myproj/%' matches '/home/u/myproj/src'
    assert result["zone"] == "GREEN"
    assert "cwd:" in result["detail"]


def test_no_match_anywhere_is_amber(tmp_path):
    """All three steps find zero rows → AMBER (not RED — index is fine)."""
    backend = _build_index(tmp_path, [
        {"id": "a", "repository": "other/proj", "cwd": "/elsewhere"},
    ])
    with patch("session_recall.health.dim_repo_coverage.detect_repo",
               return_value="my/proj"), \
         patch("session_recall.health.dim_repo_coverage.os.getcwd",
               return_value="/nowhere"):
        result = dim_repo_coverage.check(backend=backend)
    assert result["zone"] == "AMBER"
    assert "0 sessions" in result["detail"]


def test_step1_zero_falls_through_to_step2(tmp_path):
    """If git remote matches no rows, step 2 should still get its chance."""
    backend = _build_index(tmp_path, [
        {"id": "a", "repository": "auto-memory-main", "cwd": "/x/auto-memory-main"},
    ])
    with patch("session_recall.health.dim_repo_coverage.detect_repo",
               return_value="github-user/auto-memory-main"), \
         patch("session_recall.health.dim_repo_coverage.os.getcwd",
               return_value="/x/auto-memory-main"):
        result = dim_repo_coverage.check(backend=backend)
    assert result["zone"] == "GREEN"
