"""Tests for health/dim_corpus.py — backend-aware thresholds."""
import sqlite3

from session_recall.backends import Backend
from session_recall.db.schema_check import EXPECTED_SCHEMA
from session_recall.health import dim_corpus


def _make_backend_with_sessions(tmp_path, count: int,
                                thresholds: tuple[int, int]) -> Backend:
    db = tmp_path / "x.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE sessions (id TEXT, repository TEXT, branch TEXT, "
        "summary TEXT, created_at TEXT, updated_at TEXT)"
    )
    for i in range(count):
        conn.execute("INSERT INTO sessions(id) VALUES (?)", (f"s{i}",))
    conn.commit()
    conn.close()
    return Backend(name="t", db_path=str(db), instructions_path="",
                   expected_schema=EXPECTED_SCHEMA,
                   corpus_thresholds=thresholds)


def test_claude_low_thresholds_score_green_at_modest_count(tmp_path):
    """Claude's (5, 2) thresholds: 19 sessions → GREEN 10 (capped)."""
    backend = _make_backend_with_sessions(tmp_path, 19, thresholds=(5, 2))
    result = dim_corpus.check(backend=backend)
    assert result["zone"] == "GREEN"
    assert result["score"] == 10.0


def test_just_at_green_threshold_scores_at_least_seven(tmp_path):
    """Hitting exactly the green threshold should score 7+, GREEN."""
    backend = _make_backend_with_sessions(tmp_path, 5, thresholds=(5, 2))
    result = dim_corpus.check(backend=backend)
    assert result["zone"] == "GREEN"
    assert result["score"] >= 7


def test_copilot_default_thresholds_score_amber_at_modest_count(tmp_path):
    """Copilot's (50, 10) defaults: 19 sessions → AMBER (regression guard)."""
    backend = _make_backend_with_sessions(tmp_path, 19, thresholds=(50, 10))
    result = dim_corpus.check(backend=backend)
    assert result["zone"] == "AMBER"
    assert result["score"] < 10


def test_below_amber_threshold_is_red(tmp_path):
    backend = _make_backend_with_sessions(tmp_path, 1, thresholds=(10, 3))
    result = dim_corpus.check(backend=backend)
    assert result["zone"] == "RED"


def test_no_backend_falls_back_to_default_thresholds(tmp_path, monkeypatch):
    """When backend=None the dim must read DB_PATH and use Copilot defaults."""
    db = tmp_path / "y.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE sessions (id TEXT)")
    for i in range(5):
        conn.execute("INSERT INTO sessions(id) VALUES (?)", (f"s{i}",))
    conn.commit()
    conn.close()
    monkeypatch.setattr("session_recall.health.dim_corpus.DB_PATH", str(db))
    result = dim_corpus.check(backend=None)
    # 5 sessions vs default (50, 10) → RED
    assert result["zone"] == "RED"
