"""Manually refresh the Claude Code index from ~/.claude/projects/**/*.jsonl.

Normally the index is brought in sync transparently before every other
command via Backend.ensure_index(). This subcommand exposes a `--full` rebuild
for debugging schema drift, and a `--verbose` mode for inspecting which files
were touched.
"""
from __future__ import annotations

import sys

from ..ingest import run as ingest_run
from ..backends.claude_code import (
    DEFAULT_INDEX_DB, DEFAULT_PROJECTS_DIR,
)
from ..util.format_output import fmt_json


def run(args, backend=None) -> int:
    if backend is not None and backend.name == "copilot":
        print("note: ingest is a Claude-only command. Copilot CLI maintains its own DB.",
              file=sys.stderr)
        return 0

    db_path = backend.db_path if backend is not None else DEFAULT_INDEX_DB
    # Claude backend stores the projects dir as a closure; we need it explicitly
    # here for the manual rebuild path. Read the env override directly.
    import os
    projects_dir = os.environ.get("SESSION_RECALL_CLAUDE_PROJECTS",
                                  DEFAULT_PROJECTS_DIR)

    summary = ingest_run.run_incremental(
        db_path=db_path,
        projects_dir=projects_dir,
        full=getattr(args, "full", False),
        verbose=getattr(args, "verbose", False),
    )

    if getattr(args, "json", False):
        print(fmt_json(summary))
    else:
        mode = "full rebuild" if getattr(args, "full", False) else "incremental"
        print(f"Ingest ({mode}): "
              f"{summary['files_ingested']}/{summary['files_seen']} files updated, "
              f"{summary['files_skipped']} unchanged, "
              f"{summary['errors']} errors")
    return 0 if summary["errors"] == 0 else 1
