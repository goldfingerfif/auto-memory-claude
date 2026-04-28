# Deploy auto-memory

auto-memory is a zero-dependency Python CLI that gives any AI coding agent low-token recall (~50–150 tokens plain text, ~1,400 with `--json`) of recent sessions, files, and checkpoints. It supports two backends today:

- **Claude Code** — reads `~/.claude/projects/**/*.jsonl` (auto-ingested into a local SQLite index)
- **GitHub Copilot CLI** — reads `~/.copilot/session-store.db` (Copilot maintains the DB)

You can use one, the other, or both. `session-recall` auto-detects which backend is present, or you can force one with `--backend claude|copilot`.

## Prerequisites

```bash
python3 --version   # must be 3.10+
```

One of these package managers must be available (checked in priority order):

```bash
uv --version     # preferred
pipx --version   # fallback 1
pip --version    # fallback 2
```

Plus, depending on which agent you're wiring up:

```bash
claude --version    # for Claude Code integration
copilot --version   # for Copilot CLI integration
```

## Install the CLI

The CLI is the same regardless of which backend you choose. Run the first command that succeeds:

```bash
# Preferred — uv
uv tool install --force --editable .

# Fallback 1 — pipx
pipx install --force -e .

# Fallback 2 — pip
python3 -m pip install --user --force-reinstall -e .
```

Verify:

```bash
which session-recall
session-recall --help
```

If `which session-recall` returns nothing, see Troubleshooting.

## Pick your agent

### A) Claude Code

Claude Code stores transcripts as JSONL files under `~/.claude/projects/`. `session-recall` ingests these into a local SQLite index automatically on every CLI call.

**Step 1 — Verify the projects dir exists:**

```bash
ls ~/.claude/projects/
```

If empty or missing, run a Claude Code session first (`claude` from any project directory) — `~/.claude/projects/<encoded-cwd>/<sessionId>.jsonl` will be created.

**Step 2 — Smoke test:**

```bash
session-recall --backend claude ingest --verbose
session-recall --backend claude list --json --limit 3
session-recall --backend claude health --json
```

The first ingest may take a few seconds; subsequent calls re-touch only changed JSONL files.

**Step 3 — Wire into Claude Code's instruction file:**

Append the block from [`claude-code-instructions-template.md`](../claude-code-instructions-template.md) to your `~/.claude/CLAUDE.md` (global) or a project-level `CLAUDE.md`. From now on every Claude Code session begins with `session-recall files`/`list`/`search` calls before doing anything else.

**Step 4 (optional) — SessionStart hook:**

For zero per-query latency, install the snippet at [`deploy/claude-code-hook.json`](claude-code-hook.json) into your `~/.claude/settings.json` `hooks` object. With the hook, ingest runs once at session boot.

### B) GitHub Copilot CLI

Copilot CLI maintains its own SQLite store at `~/.copilot/session-store.db`. `session-recall` reads it directly read-only.

**Step 1 — Windows (WSL2) only: enable the session store**

On Windows 11 + WSL2, Copilot CLI does not create `session-store.db` by default:

1. Start Copilot: `copilot`
2. Inside the session: `/experimental`
3. Select **SESSION_STORE**
4. Verify: `ls ~/.copilot/session-store.db`

This is a one-time setup. macOS/Linux users skip this step.

**Step 2 — Smoke test:**

```bash
session-recall --backend copilot list --json --limit 3
session-recall --backend copilot health --json
session-recall --backend copilot schema-check
```

**Step 3 — Wire into Copilot's instruction file:**

Append the block from [`copilot-instructions-template.md`](../copilot-instructions-template.md) to `~/.copilot/copilot-instructions.md`.

### C) Both

`session-recall` auto-detects: if both stores are present, Claude Code wins by default (newer-first; pass `--backend copilot` to override). Wire both instruction blocks into their respective files and you're done.

## Verify Installation

Run all three checks for whichever backend(s) you wired up:

```bash
session-recall health           # all dimensions GREEN (or N/A on Copilot for Index Ingest)
session-recall list --json      # at least one session
session-recall schema-check     # exit 0
```

## Troubleshooting

### `error: database not found` (Copilot)

Copilot CLI hasn't created the session store yet. On WSL2, you must enable the experimental SESSION_STORE feature first (see B/Step 1).

### `error: database not found` (Claude)

`~/.claude/projects/` is empty. Run any Claude Code session first; the JSONL transcript is what `session-recall` ingests.

### `command not found: session-recall`

PATH issue. Check that the install dir is on PATH:

```bash
echo "$PATH" | tr ':' '\n' | grep -q '.local/bin' && echo "OK" || echo "MISSING"
```

If missing, add it and retry:

```bash
export PATH="$HOME/.local/bin:$PATH"
which session-recall
```

### `schema-check` fails (exit code 2)

Copilot: see [UPGRADE-COPILOT-CLI.md](../UPGRADE-COPILOT-CLI.md).
Claude: see [UPGRADE-CLAUDE-CODE.md](../UPGRADE-CLAUDE-CODE.md). Most often a forced rebuild fixes it: `session-recall ingest --full`.

### No sessions found

Normal on first use. Run a session in your agent, then retry.
