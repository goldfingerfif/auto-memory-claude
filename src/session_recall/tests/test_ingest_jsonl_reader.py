"""Tests for ingest/jsonl_reader.py — line streaming and content extraction."""
from pathlib import Path

from session_recall.ingest.jsonl_reader import (
    iter_lines, extract_text, extract_tool_uses,
)


FIXTURE = Path(__file__).parent / "fixtures" / "claude_session.jsonl"


def test_iter_lines_skips_malformed():
    """Bad JSON lines are dropped silently; well-formed ones come through."""
    records = list(iter_lines(FIXTURE))
    assert len(records) >= 6  # 7 valid lines in the fixture
    for idx, rec in records:
        assert isinstance(idx, int)
        assert isinstance(rec, dict)


def test_iter_lines_respects_start_line():
    """start_line skips already-seen prefixes (used by incremental driver)."""
    full = list(iter_lines(FIXTURE))
    if len(full) < 3:
        return
    skipped = list(iter_lines(FIXTURE, start_line=2))
    # First record after skip should have idx >= 2
    assert skipped[0][0] >= 2


def test_extract_text_handles_strings():
    assert extract_text("hello") == "hello"


def test_extract_text_handles_blocks():
    blocks = [{"type": "text", "text": "first"},
              {"type": "tool_use", "name": "Read"},
              {"type": "text", "text": "second"}]
    assert extract_text(blocks) == "first\nsecond"


def test_extract_text_skips_thinking_blocks():
    blocks = [{"type": "text", "text": "visible"},
              {"type": "thinking", "thinking": "private"}]
    assert "private" not in extract_text(blocks)


def test_extract_text_handles_none():
    assert extract_text(None) == ""


def test_extract_tool_uses_returns_only_tool_use_blocks():
    blocks = [{"type": "text", "text": "x"},
              {"type": "tool_use", "name": "Read", "input": {"file_path": "/a"}},
              {"type": "tool_use", "name": "Write", "input": {"file_path": "/b"}}]
    tools = extract_tool_uses(blocks)
    assert len(tools) == 2
    assert {t["name"] for t in tools} == {"Read", "Write"}


def test_extract_tool_uses_handles_string_content():
    """A string content (no blocks) yields no tool uses."""
    assert extract_tool_uses("hello") == []
