# auto-memory — Claude Code Instructions Template

> **Note:** For installation, use [`deploy/install.md`](deploy/install.md) — it covers Claude Code, Copilot CLI, and the dual-agent path.

This file contains the raw instruction block for manual reference. Append it to your `~/.claude/CLAUDE.md` (or a project-level `CLAUDE.md`) so every Claude Code session starts with progressive recall.

---

## Progressive Session Recall — RUN FIRST ON EVERY PROMPT

**Run `session-recall` FIRST on every prompt before doing anything else.** It costs ~50 tokens and prevents expensive blind searches.

```bash
session-recall files --json --limit 10  # recently touched files
session-recall files --days 7 --json    # files touched in last 7 days
session-recall list --json --limit 5    # recent sessions
session-recall list --days 2 --json     # sessions from last 2 days
session-recall search '<term>' --json   # full-text search
session-recall search '<term>' --days 5 # search last 5 days only
session-recall checkpoints --days 3     # checkpoints from last 3 days
session-recall show <id> --json         # drill into one session
session-recall health --json            # 10-dimension health check
session-recall ingest                   # refresh index from JSONL transcripts
session-recall schema-check             # validate index schema
```

**`--days N` works on all 4 query commands** (`list`, `files`, `checkpoints`, `search`) — filters to sessions/files/checkpoints from the last N days.

The Claude Code backend ingests `~/.claude/projects/**/*.jsonl` into a local SQLite index at `~/.claude/.session-recall.db` automatically before every command (incremental, idempotent, ~50 ms cold). You should never need to run `session-recall ingest` manually.

Only use filesystem tools (grep, glob, find) if `session-recall` returns nothing useful.
If `session-recall` errors, continue silently — it's a convenience, not a blocker.

---

## Optional: SessionStart hook for zero per-query latency

If you want recall to be available with zero ingest cost during a session, add this hook to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "session-recall ingest"
          }
        ]
      }
    ]
  }
}
```

With the hook installed, ingest runs once at session boot and every subsequent `session-recall` call skips the disk-walk step entirely.
