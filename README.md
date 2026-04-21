# auto-memory

> **Your AI coding agent never forgets.**

Progressive session disclosure CLI for GitHub Copilot CLI. Queries your local `~/.copilot/session-store.db` to recall what you worked on across sessions — so your agent always has context.

## Why

Copilot CLI stores session history locally but has no built-in way to query it. `auto-memory` gives you (and the agent) structured access to past sessions, files, and checkpoints — enabling progressive context recall without MCP servers or hooks.

## Install

Tell your AI agent:

> Read `deploy/install.md` and follow every step.

Or run manually:

```bash
./install.sh
```

See [`deploy/install.md`](deploy/install.md) for full instructions, agent integration, and troubleshooting.

## Usage

```bash
# List recent sessions for current repo
auto-memory list --json

# Show details for a session (prefix match)
auto-memory show f662 --json

# Full-text search across turns
auto-memory search "SQLITE_BUSY" --json

# Recently touched files
auto-memory files --json

# Recent checkpoints
auto-memory checkpoints --json

# 8-dimension health check
auto-memory health

# Validate DB schema (run after Copilot CLI upgrades)
auto-memory schema-check
```

## Health Check

```
Dim Name                   Zone     Score  Detail
----------------------------------------------------------------------
 1  DB Freshness           🟢 GREEN   8.0  15.8h old
 2  Schema Integrity       🟢 GREEN  10.0  All tables/columns OK
 3  Query Latency          🟢 GREEN  10.0  1ms
 4  Corpus Size            🟢 GREEN  10.0  399 sessions
 5  Summary Coverage       🟢 GREEN   7.4  92% (367/399)
 6  Repo Coverage          🟢 GREEN  10.0  8 sessions for owner/repo
 7  Concurrency            🟢 GREEN  10.0  busy=0.0%, p95=48ms
 8  E2E Probe              🟢 GREEN  10.0  list→show OK
```

## Design

- **Zero dependencies** — stdlib only (sqlite3, json, argparse)
- **Read-only** — never writes to `~/.copilot/session-store.db`
- **WAL-safe** — exponential backoff retry on SQLITE_BUSY (50→150→450ms)
- **Schema-aware** — validates expected schema on every call, fails fast on drift
- **Telemetry** — ring buffer of last 100 invocations for concurrency monitoring

## How It Works

auto-memory is **instruction-driven** — it doesn't use hooks, MCP servers, or plugins. Instead, you add a block of text to your Copilot CLI instruction file that tells the agent to run `auto-memory` commands at the start of every prompt.

```
┌─────────────────────────────────────────────────────────┐
│  You install auto-memory (puts CLI on your PATH)        │
│                         ▼                               │
│  You paste the template into copilot-instructions.md    │
│                         ▼                               │
│  Copilot CLI reads instructions on every session start  │
│                         ▼                               │
│  Agent sees: "Run auto-memory FIRST on every prompt"    │
│                         ▼                               │
│  Agent runs: auto-memory files --json --limit 10        │
│              auto-memory list --json --limit 5          │
│                         ▼                               │
│  Agent gets structured context about your past sessions │
│  before answering — no blind searches needed            │
└─────────────────────────────────────────────────────────┘
```

**Why instructions instead of hooks?** Portable, zero infrastructure, works with any agent that reads instruction files. No config, no daemon, no server — just a CLI tool and a text block.

## Agent Integration

### Step 1: Install auto-memory

```bash
./install.sh
# or: uv pip install -e .
# or: pip install -e .
```

### Step 2: Add instructions to Copilot CLI

Copilot CLI reads `~/.copilot/copilot-instructions.md` at the start of every session. This file tells the agent what tools to use and how to behave.

Copy the template into your instruction file:

```bash
# Create the file if it doesn't exist
mkdir -p ~/.copilot
touch ~/.copilot/copilot-instructions.md

# Append the auto-memory instructions
cat copilot-instructions-template.md >> ~/.copilot/copilot-instructions.md
```

The template is in [`copilot-instructions-template.md`](copilot-instructions-template.md) — it tells the agent to run `auto-memory` commands before each prompt to check for relevant past context.

### Step 3: Verify

```bash
# In a Copilot CLI session, ask:
"Run auto-memory health and show me the output"
```

If the agent runs the command and shows health results, integration is working.

See [`UPGRADE-COPILOT-CLI.md`](UPGRADE-COPILOT-CLI.md) for schema validation after Copilot CLI upgrades.

## Disclaimer

This is an independent open-source project. It is **not** affiliated with, endorsed by, or supported by Microsoft, GitHub, or any other company. There is no official support — use at your own risk. Contributions and issues are welcome on GitHub.

## License

MIT
