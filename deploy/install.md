# Deploy auto-memory

auto-memory is a zero-dependency Python CLI that queries `~/.copilot/session-store.db` for progressive session recall. Install it once, wire it into Copilot CLI instructions, and every future agent session starts with full context.

## Prerequisites

Verify these before proceeding. Stop and report if any fail.

```bash
python3 --version   # must be 3.10+
copilot --version   # Copilot CLI must be installed
```

One of these package managers must be available (checked in priority order):

```bash
uv --version     # preferred
pipx --version   # fallback 1
pip --version     # fallback 2
```

## Install

### Step 1 — Clone or navigate to the repo

If the repo is not already local, clone it:

```bash
git clone <auto-memory-repo-url>
cd auto-memory
```

If already local, `cd` into the repo root.

### Step 2 — Install the CLI

Run the first command that succeeds. Stop after one succeeds.

```bash
# Preferred — uv
uv tool install --force --editable .

# Fallback 1 — pipx
pipx install --force -e .

# Fallback 2 — pip
python3 -m pip install --user --force-reinstall -e .
```

### Step 3 — Verify install

Run both commands. Both must succeed.

```bash
which auto-memory
auto-memory schema-check
```

If `which auto-memory` returns nothing, see Troubleshooting below.

## Agent Integration — Add to Copilot Instructions

This step wires auto-memory into every future agent session by appending instructions to `~/.copilot/copilot-instructions.md`.

### Step 1 — Ensure the file exists

```bash
mkdir -p ~/.copilot
touch ~/.copilot/copilot-instructions.md
```

### Step 2 — Check for duplicates

Search `~/.copilot/copilot-instructions.md` for the string `Progressive Session Recall`. If it already exists, **skip Step 3 entirely** — the block is already present.

### Step 3 — Append the instruction block

Append this exact block to the end of `~/.copilot/copilot-instructions.md`:

```markdown
## Progressive Session Recall — RUN FIRST ON EVERY PROMPT

**Run `auto-memory` FIRST on every prompt before doing anything else.** It costs ~50 tokens and prevents expensive blind searches.

```bash
auto-memory files --json --limit 10  # recently touched files
auto-memory files --days 7 --json    # files touched in last 7 days
auto-memory list --json --limit 5    # recent sessions
auto-memory list --days 2 --json     # sessions from last 2 days
auto-memory search '<term>' --json   # full-text search
auto-memory search '<term>' --days 5 # search last 5 days only
auto-memory checkpoints --days 3     # checkpoints from last 3 days
auto-memory show <id> --json         # drill into one session
auto-memory health --json            # 8-dimension health check
auto-memory schema-check             # validate DB schema (run after Copilot CLI upgrade)
```

**`--days N` works on all 4 query commands** (`list`, `files`, `checkpoints`, `search`) — filters to sessions/files/checkpoints from the last N days.

Only use filesystem tools (grep, glob, find) if auto-memory returns nothing useful.
If `auto-memory` errors, continue silently — it's a convenience, not a blocker.
```

## Verify Installation

Run all three checks. All must pass.

```bash
auto-memory health          # all dimensions should show GREEN
auto-memory list --json     # should return at least one session
auto-memory schema-check    # must exit 0
```

If `auto-memory list --json` returns zero sessions, that is normal on a fresh install — Copilot CLI needs at least one completed session first.

## Troubleshooting

### `command not found: auto-memory`

PATH issue. Check that `~/.local/bin` is on PATH:

```bash
echo "$PATH" | tr ':' '\n' | grep -q '.local/bin' && echo "OK" || echo "MISSING"
```

If missing, add it and retry:

```bash
export PATH="$HOME/.local/bin:$PATH"
which auto-memory
```

If still not found, re-run install with `uv tool install --force --editable .` from the repo root.

### `schema-check` fails (exit code 2)

The Copilot CLI DB schema has drifted from what auto-memory expects. This usually happens after a Copilot CLI upgrade. See [UPGRADE-COPILOT-CLI.md](../UPGRADE-COPILOT-CLI.md) for the full procedure.

### No sessions found

Normal on first use. Copilot CLI needs at least one completed session before auto-memory has anything to query. Run a Copilot CLI session, then retry.

## Upgrading Copilot CLI

After any Copilot CLI upgrade, run:

```bash
auto-memory schema-check
```

If it exits 0, no action needed. If it fails, follow the full upgrade procedure in [UPGRADE-COPILOT-CLI.md](../UPGRADE-COPILOT-CLI.md).
