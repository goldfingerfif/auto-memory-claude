# auto-memory — Copilot Instructions Template

> **Note:** For installation, use [`deploy/install.md`](deploy/install.md) — it handles everything including appending this template automatically.

This file contains the raw instruction block for manual reference. Copy the block below into `~/.copilot/copilot-instructions.md` if you prefer manual setup.

---

## Progressive Session Recall — RUN FIRST ON EVERY PROMPT

**Run `session-recall` FIRST on every prompt before doing anything else.** It costs ~50–150 tokens for the cheap (plain-text) calls and prevents expensive blind searches.

```bash
session-recall files --limit 10         # recently touched files (~120 tokens)
session-recall files --days 7           # files touched in last 7 days
session-recall list --limit 5           # recent sessions (~110 tokens)
session-recall list --days 2            # sessions from last 2 days
session-recall search '<term>'          # full-text search
session-recall search '<term>' --days 5 # search last 5 days only
session-recall checkpoints --days 3     # checkpoints from last 3 days
session-recall show <id> --json         # drill into one session
session-recall health --json            # 10-dimension health check (Index Ingest is N/A on Copilot)
session-recall schema-check             # validate DB schema (run after Copilot CLI upgrade)
# Add --json to any cheap query when you need to parse the result programmatically (~1,400+ tokens for files/list)
```

**`--days N` works on all 4 query commands** (`list`, `files`, `checkpoints`, `search`) — filters to sessions/files/checkpoints from the last N days.

Only use filesystem tools (grep, glob, find) if session-recall returns nothing useful.
If `session-recall` errors, continue silently — it's a convenience, not a blocker.
