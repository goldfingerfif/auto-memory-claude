"""Walk a parsed JSONL and assemble Copilot-shape rows.

Inputs : an iterable of (line_index, record) tuples from jsonl_reader.
Outputs: dataclass rows ready to INSERT into the index DB.

Mapping summary
---------------
  user record               → start-of-turn signal; user_message text
  assistant record          → in-turn assistant_response text;
                              tool_use blocks → session_files rows
  type:"summary" record     → preferred sessions.summary value
  type:"plan_mode" record   → checkpoint candidate
  every record              → contributes to created_at/updated_at, branch, cwd

A "turn" = one user message followed by zero-or-more assistant messages until
the next user message (matching the Copilot semantics of `turns`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import re

from .jsonl_reader import extract_text, extract_tool_uses


FILE_TOOLS = {"Read", "Write", "Edit", "NotebookEdit"}

# Strip Claude Code command preambles (slash commands + caveats) when deriving
# a summary from the first user message — otherwise every /init / /plan session
# gets the same opaque "<command-message>init</command-message>" snippet.
_PREAMBLE_TAGS_RE = re.compile(
    r"<(?:command-message|command-name|command-args|local-command-stdout|"
    r"local-command-caveat|system-reminder|user-prompt-submit-hook)\b[^>]*>"
    r"[\s\S]*?</(?:command-message|command-name|command-args|local-command-stdout|"
    r"local-command-caveat|system-reminder|user-prompt-submit-hook)>",
    re.IGNORECASE,
)


def _derive_summary(text: str) -> str:
    """Strip Claude Code preambles, return the first ~200 chars of real content."""
    cleaned = _PREAMBLE_TAGS_RE.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:200]


@dataclass
class SessionRows:
    session_id: str = ""
    cwd: str = ""
    branch: str = ""
    summary: str = ""               # may be a derived '~'-prefixed snippet
    summary_is_native: bool = False  # True only if a type:"summary" record was found
    created_at: str = ""
    updated_at: str = ""
    turns: list[dict] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    refs: list[dict] = field(default_factory=list)
    checkpoints: list[dict] = field(default_factory=list)
    last_line: int = 0


def build(records: Iterable[tuple[int, dict]], existing: SessionRows | None = None) -> SessionRows:
    """Fold records into a SessionRows.

    Pass an existing SessionRows to extend it (used for incremental ingest:
    the driver loads the previous state, then continues parsing only new lines).
    """
    rows = existing if existing is not None else SessionRows()
    current_turn: dict | None = (
        rows.turns[-1] if rows.turns and rows.turns[-1].get("_open") else None
    )
    file_keys: set[tuple[str, str]] = {(f["file_path"], f["tool_name"]) for f in rows.files}

    for idx, rec in records:
        rows.last_line = idx + 1
        if not isinstance(rec, dict):
            continue
        sid = rec.get("sessionId")
        if sid and not rows.session_id:
            rows.session_id = sid
        cwd = rec.get("cwd")
        if cwd and not rows.cwd:
            rows.cwd = cwd
        branch = rec.get("gitBranch")
        if branch and not rows.branch:
            rows.branch = branch
        ts = rec.get("timestamp")
        if ts:
            if not rows.created_at:
                rows.created_at = ts
            rows.updated_at = ts

        rtype = rec.get("type")
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else None

        if rtype == "summary" and isinstance(rec.get("summary"), str):
            rows.summary = rec["summary"][:500]
            rows.summary_is_native = True
            continue

        if rtype == "user" and msg:
            text = extract_text(msg.get("content"))
            if not text:
                continue
            # New turn
            current_turn = {
                "turn_index": len(rows.turns),
                "user_message": text,
                "assistant_response": "",
                "timestamp": ts or "",
                "_open": True,
            }
            rows.turns.append(current_turn)
            # First user message with real content becomes the derived summary
            if not rows.summary:
                snippet = _derive_summary(text)
                if snippet:
                    rows.summary = f"~{snippet}"
            continue

        if rtype == "assistant" and msg:
            content = msg.get("content")
            text = extract_text(content)
            if current_turn is None:
                # Stray assistant before any user — start a synthetic turn
                current_turn = {
                    "turn_index": len(rows.turns),
                    "user_message": "",
                    "assistant_response": "",
                    "timestamp": ts or "",
                    "_open": True,
                }
                rows.turns.append(current_turn)
            if text:
                if current_turn["assistant_response"]:
                    current_turn["assistant_response"] += "\n" + text
                else:
                    current_turn["assistant_response"] = text
            for tu in extract_tool_uses(content):
                name = tu.get("name", "")
                tinput = tu.get("input") if isinstance(tu.get("input"), dict) else {}
                if name in FILE_TOOLS:
                    fpath = tinput.get("file_path")
                    if fpath:
                        key = (fpath, name)
                        if key not in file_keys:
                            file_keys.add(key)
                            rows.files.append({
                                "file_path": fpath,
                                "tool_name": name,
                                "turn_index": current_turn["turn_index"],
                                "first_seen_at": ts or "",
                            })
            continue

        if rtype == "plan_mode":
            title = ""
            if isinstance(rec.get("plan"), str):
                first_line = rec["plan"].splitlines()[0] if rec["plan"] else ""
                title = first_line[:120]
            rows.checkpoints.append({
                "checkpoint_number": len(rows.checkpoints) + 1,
                "title": title or f"Plan #{len(rows.checkpoints) + 1}",
                "overview": (rec.get("plan") or "")[:1000],
                "created_at": ts or "",
            })
            continue

    # All built turns from the last completed pass should be marked closed once
    # we move on; the in-progress turn (if any) keeps _open=True so a future
    # incremental pass can append to it.
    for t in rows.turns[:-1]:
        t["_open"] = False
    return rows
