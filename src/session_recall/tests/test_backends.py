"""Tests for backends/__init__.py — detection precedence & registry."""
from unittest.mock import patch

import pytest

from session_recall import backends


def test_explicit_name_wins(monkeypatch):
    monkeypatch.setenv("SESSION_RECALL_BACKEND", "copilot")
    monkeypatch.setenv("SESSION_RECALL_DB", "/nonexistent.db")
    b = backends.detect("claude")
    assert b.name == "claude"


def test_env_var_used(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_RECALL_BACKEND", "copilot")
    monkeypatch.setenv("SESSION_RECALL_DB", str(tmp_path / "x.db"))
    b = backends.detect(None)
    assert b.name == "copilot"


def test_unknown_backend_exits(monkeypatch):
    monkeypatch.delenv("SESSION_RECALL_BACKEND", raising=False)
    with pytest.raises(SystemExit):
        backends.detect("not-a-backend")


def test_autodetect_prefers_claude_when_both(monkeypatch):
    monkeypatch.delenv("SESSION_RECALL_BACKEND", raising=False)
    monkeypatch.delenv("SESSION_RECALL_DB", raising=False)
    monkeypatch.delenv("SESSION_RECALL_CLAUDE_PROJECTS", raising=False)
    with patch("session_recall.backends._copilot_present", return_value=True), \
         patch("session_recall.backends._claude_present", return_value=True):
        b = backends.detect(None)
    assert b.name == "claude"


def test_autodetect_uses_only_present(monkeypatch):
    monkeypatch.delenv("SESSION_RECALL_BACKEND", raising=False)
    monkeypatch.delenv("SESSION_RECALL_DB", raising=False)
    monkeypatch.delenv("SESSION_RECALL_CLAUDE_PROJECTS", raising=False)
    with patch("session_recall.backends._copilot_present", return_value=True), \
         patch("session_recall.backends._claude_present", return_value=False):
        assert backends.detect(None).name == "copilot"
    with patch("session_recall.backends._copilot_present", return_value=False), \
         patch("session_recall.backends._claude_present", return_value=True):
        assert backends.detect(None).name == "claude"


def test_backend_freshness_signal_default_uses_db_path(tmp_path):
    db = tmp_path / "store.db"
    db.write_bytes(b"")
    b = backends.Backend(name="x", db_path=str(db), instructions_path="",
                         expected_schema={})
    assert b.freshness_signal() is not None


def test_backend_freshness_signal_none_when_missing(tmp_path):
    b = backends.Backend(name="x", db_path=str(tmp_path / "missing.db"),
                         instructions_path="", expected_schema={})
    assert b.freshness_signal() is None


def test_registry_contains_known_backends():
    assert "copilot" in backends.REGISTRY
    assert "claude" in backends.REGISTRY


def test_explicit_overrides_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_RECALL_BACKEND", "claude")
    monkeypatch.setenv("SESSION_RECALL_DB", str(tmp_path / "stub.db"))
    b = backends.detect("copilot")
    assert b.name == "copilot"
