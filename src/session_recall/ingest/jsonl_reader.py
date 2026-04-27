"""Streaming JSONL reader for Claude Code session transcripts.

Each line in `~/.claude/projects/<encoded-cwd>/<sessionId>.jsonl` is one JSON
object. Top-level shape (only fields we care about):

    {
      "type": "user" | "assistant" | "tool_use" | "tool_result" | "summary" | ...,
      "message": {"role": "...", "content": str | [block, ...]},
      "uuid": "...",
      "parentUuid": "...",
      "sessionId": "...",
      "timestamp": "2026-04-27T17:41:05.148Z",
      "cwd": "...",
      "gitBranch": "..."
    }

This module is the single source of truth for parsing those records. It is
tolerant: malformed JSON lines are skipped (and counted) rather than raising.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def iter_lines(jsonl_path: str | Path, start_line: int = 0) -> Iterator[tuple[int, dict]]:
    """Yield (line_index, parsed_dict) for each well-formed JSON line.

    Skips malformed lines silently (caller can wrap with logging if desired).
    `start_line` lets the incremental driver resume from a prior checkpoint
    without re-parsing already-ingested lines.
    """
    p = Path(jsonl_path)
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for idx, raw in enumerate(fh):
            if idx < start_line:
                continue
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield idx, json.loads(raw)
            except json.JSONDecodeError:
                continue


def extract_text(content) -> str:
    """Pull the plain-text portion out of a message.content field.

    Claude content can be:
      - a string (user messages typically)
      - a list of blocks: [{"type":"text","text":"..."}, {"type":"tool_use",...}]
    Tool-use and tool-result blocks are skipped here; only readable text is
    concatenated. Returns '' if nothing extractable.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                t = block.get("text")
                if isinstance(t, str):
                    parts.append(t)
            elif btype == "thinking":
                # Skip — not meaningful for recall output
                continue
        return "\n".join(parts)
    return ""


def extract_tool_uses(content) -> list[dict]:
    """Return the tool_use blocks from message.content (or empty list)."""
    if not isinstance(content, list):
        return []
    out = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            out.append(block)
    return out
