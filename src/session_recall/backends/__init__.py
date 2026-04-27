"""Backend abstraction — pick which session store to query.

A Backend bundles the read-only DB path, the schema we expect to find there,
an `ensure_index()` hook for backends that maintain their own index from
upstream data (Claude Code), and a `freshness_signal()` callable that returns
the unix-timestamp of the upstream data (so dim_freshness scores the actual
agent activity, not just our local index file).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


def _default_freshness(db_path: str) -> Callable[[], Optional[float]]:
    """Default: stat the DB file. Works for Copilot (real store)."""
    def _f() -> Optional[float]:
        try:
            return os.path.getmtime(db_path)
        except OSError:
            return None
    return _f


@dataclass
class Backend:
    name: str
    db_path: str
    instructions_path: str
    expected_schema: dict
    ensure_index: Callable[[], None] = field(default=lambda: None)
    freshness_signal: Optional[Callable[[], Optional[float]]] = None

    def __post_init__(self):
        if self.freshness_signal is None:
            self.freshness_signal = _default_freshness(self.db_path)


def _copilot() -> Backend:
    from .copilot import build
    return build()


def _claude() -> Backend:
    from .claude_code import build
    return build()


REGISTRY: dict[str, Callable[[], Backend]] = {
    "copilot": _copilot,
    "claude": _claude,
}


def _copilot_present() -> bool:
    override = os.environ.get("SESSION_RECALL_DB")
    if override:
        return Path(override).exists()
    return (Path.home() / ".copilot" / "session-store.db").exists()


def _claude_present() -> bool:
    override = os.environ.get("SESSION_RECALL_CLAUDE_PROJECTS")
    if override:
        return Path(override).exists()
    return (Path.home() / ".claude" / "projects").exists()


def detect(explicit: str | None = None) -> Backend:
    """Return the active Backend. Precedence:
       1. explicit name (CLI flag)
       2. SESSION_RECALL_BACKEND env var
       3. presence of stores on disk (claude > copilot when both present)
       4. fall back to copilot (legacy behavior — empty path errors fail loud)
    """
    name = (explicit or os.environ.get("SESSION_RECALL_BACKEND") or "").strip().lower()
    if name:
        if name not in REGISTRY:
            print(f"error: unknown backend '{name}' (choices: {', '.join(REGISTRY)})",
                  file=sys.stderr)
            sys.exit(2)
        return REGISTRY[name]()

    has_claude = _claude_present()
    has_copilot = _copilot_present()
    if has_claude and has_copilot:
        print("note: both Claude Code and Copilot stores detected; using claude. "
              "Pass --backend copilot to override.", file=sys.stderr)
        return REGISTRY["claude"]()
    if has_claude:
        return REGISTRY["claude"]()
    if has_copilot:
        return REGISTRY["copilot"]()
    return REGISTRY["copilot"]()
