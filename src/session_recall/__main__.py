"""auto-memory CLI — progressive session disclosure.

Supports multiple backends:
  - copilot  — reads ~/.copilot/session-store.db (Copilot CLI maintains it)
  - claude   — reads ~/.claude/projects/**/*.jsonl, ingested into a local
               SQLite index at ~/.claude/.session-recall.db on each call

Backend selection: --backend flag > SESSION_RECALL_BACKEND env > auto-detect.
"""

import argparse
import sys
import time

from . import backends
from .config import TELEMETRY_PATH
from .util import telemetry


def _non_negative_int(v):
    """Argparse type: non-negative integer."""
    i = int(v)
    if i < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {v}")
    return i


TIER_MAP = {
    "list": 1,
    "files": 1,
    "checkpoints": 1,  # Tier 1 — cheap scan
    "search": 2,  # Tier 2 — focused search
    "show": 3,  # Tier 3 — deep dive
    "health": 0,
    "schema-check": 0,  # Tier 0 — meta/ops
    "ingest": 0,  # Tier 0 — meta/ops (Claude)
    "calibrate": 0,  # Tier 0 — meta (Phase 4)
}


def main() -> None:
    # Don't crash when stdout is a Windows cp1252 console and we emit a Unicode
    # glyph (em-dash, arrow, emoji, …). Drop the bad chars rather than the run.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    telemetry.init(TELEMETRY_PATH)
    t0 = time.monotonic()
    parser = argparse.ArgumentParser(
        prog="auto-memory", description="Query session history"
    )
    parser.add_argument(
        "--backend",
        choices=sorted(backends.REGISTRY.keys()),
        default=None,
        help="Force a specific backend (default: auto-detect)",
    )
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="Recent sessions")
    p_list.add_argument("--repo", default=None)
    p_list.add_argument("--limit", type=int, default=None)
    p_list.add_argument(
        "--days",
        type=int,
        default=None,
        help="Only include sessions from last N days (default 30)",
    )
    p_list.add_argument("--json", action="store_true")
    p_list.add_argument("--brief", action="store_true",
                        help="Drop session summary fields under --json (cheap structured output)")

    p_schema = sub.add_parser("schema-check", help="Validate DB schema")
    p_schema.add_argument("--json", action="store_true")

    p_files = sub.add_parser("files", help="Recently touched files")
    p_files.add_argument("--json", action="store_true")
    p_files.add_argument("--brief", action="store_true",
                         help="Drop session summary fields under --json (cheap structured output)")
    p_files.add_argument("--repo", default=None)
    p_files.add_argument("--limit", type=int, default=None)
    p_files.add_argument(
        "--days", type=int, default=None, help="Only include files from last N days"
    )

    p_cp = sub.add_parser("checkpoints", help="Recent checkpoints")
    p_cp.add_argument("--json", action="store_true")
    p_cp.add_argument("--brief", action="store_true",
                      help="Drop session summary fields under --json (cheap structured output)")
    p_cp.add_argument("--repo", default=None)
    p_cp.add_argument("--limit", type=int, default=None)
    p_cp.add_argument(
        "--days",
        type=int,
        default=None,
        help="Only include checkpoints from last N days",
    )

    p_show = sub.add_parser("show", help="Show session details")
    p_show.add_argument("session_id")
    p_show.add_argument("--json", action="store_true")
    p_show.add_argument("--brief", action="store_true",
                        help="Drop the summary field under --json")
    p_show.add_argument("--turns", type=_non_negative_int, default=None)
    p_show.add_argument("--full", action="store_true")

    p_search = sub.add_parser("search", help="Full-text search")
    p_search.add_argument("query")
    p_search.add_argument("--json", action="store_true")
    p_search.add_argument("--brief", action="store_true",
                          help="Drop session summary fields under --json (cheap structured output)")
    p_search.add_argument("--repo", default=None)
    p_search.add_argument("--limit", type=int, default=None)
    p_search.add_argument(
        "--days", type=int, default=None, help="Only include sessions from last N days"
    )

    p_health = sub.add_parser("health", help="Health check (9 dimensions)")
    p_health.add_argument("--json", action="store_true")

    p_ingest = sub.add_parser(
        "ingest", help="Refresh the Claude Code index from JSONL transcripts"
    )
    p_ingest.add_argument(
        "--full", action="store_true", help="Drop the index and rebuild from scratch"
    )
    p_ingest.add_argument("--verbose", "-v", action="store_true")
    p_ingest.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Resolve backend once and pass it to every command. ensure_index() is a
    # no-op for Copilot; for Claude it (incrementally) rebuilds the SQLite
    # index from JSONL before the command sees the DB.
    backend = backends.detect(args.backend)
    if args.command != "ingest":
        # `ingest --full` will handle its own rebuild path
        try:
            backend.ensure_index()
        except Exception as e:
            print(f"warning: ensure_index failed: {e}", file=sys.stderr)

    exit_code = 1
    if args.command == "list":
        from .commands.list_sessions import run

        exit_code = run(args, backend)
    elif args.command == "schema-check":
        from .commands.schema_check_cmd import run

        exit_code = run(args, backend)
    elif args.command == "files":
        from .commands.files import run

        exit_code = run(args, backend)
    elif args.command == "checkpoints":
        from .commands.checkpoints import run

        exit_code = run(args, backend)
    elif args.command == "show":
        from .commands.show_session import run

        exit_code = run(args, backend)
    elif args.command == "search":
        from .commands.search import run

        exit_code = run(args, backend)
    elif args.command == "health":
        from .commands.health import run

        exit_code = run(args, backend)
    elif args.command == "ingest":
        from .commands.ingest import run

        exit_code = run(args, backend)
    else:
        print(f"'{args.command}' not yet implemented.", file=sys.stderr)

    duration_ms = int((time.monotonic() - t0) * 1000)
    tier = TIER_MAP.get(args.command)  # None if command unknown
    qhash = None
    sid_prefix = None
    wtier = None  # Phase 4 will populate this
    if args.command == "search":
        qhash = telemetry.query_hash(getattr(args, "query", "") or "")
    elif args.command == "show":
        sid = getattr(args, "session_id", "") or ""
        sid_prefix = sid[:8] if sid else None
    telemetry.record(
        cmd=args.command,
        duration_ms=duration_ms,
        exit_code=exit_code,
        tier=tier,
        query_hash=qhash,
        session_id_prefix=sid_prefix,
        window_tier=wtier,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
