# auto-memory

## Your AI coding agent has amnesia. Here's the fix.

*~1,900 lines of Python. Zero dependencies. Saves you an hour a day.*

> Built by [Desi Villanueva](https://github.com/dezgit2025)

[![PyPI](https://img.shields.io/pypi/v/auto-memory)](https://pypi.org/project/auto-memory/)
[![CI](https://github.com/dezgit2025/auto-memory/actions/workflows/test.yml/badge.svg)](https://github.com/dezgit2025/auto-memory/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-126%20passed-brightgreen)]()

**Zero-dependency CLI that turns your AI agent's local session history into instant recall — no MCP server, read-only, schema-checked. ~50 tokens per prompt.**

**Works with:** Claude Code · GitHub Copilot CLI  
**Coming soon:** Cursor · Codex

---

### Quickstart

```bash
pip install auto-memory        # or: git clone + ./install.sh
session-recall health          # verify it works
```

Now give your agent a memory. Point it at [`deploy/install.md`](deploy/install.md) and let it cook. 🍳

---

### Backend support

`session-recall` auto-detects which agent's data is on disk and uses it. Force a specific one with `--backend claude|copilot`.

| Backend | Reads | Notes |
|---|---|---|
| Claude Code | `~/.claude/projects/**/*.jsonl` | Auto-ingested into a local SQLite index at `~/.claude/.session-recall.db` (incremental, ~50 ms cold). |
| GitHub Copilot CLI | `~/.copilot/session-store.db` | Read direct from Copilot's own store. On Windows 11 + WSL2 you must enable `/experimental` → `SESSION_STORE` first (see [`deploy/install.md`](deploy/install.md)). |

Both modes expose the same CLI: `list`, `files`, `search`, `show`, `checkpoints`, `health`, `schema-check`. The Claude backend additionally has `ingest` for forced rebuilds.

---

## The Problem

Every AI coding agent ships with a big number on the box. 200K tokens. Sounds massive. Here's what actually happens:

```
200,000  tokens — context window (theoretical max)
120,000  tokens — effective limit before context rot kicks in (~60%)
 -65,000  tokens — MCP tools
 -10,000  tokens — instruction files
=========
 ~45,000  tokens — what you ACTUALLY have before quality degrades
```

LLMs don't degrade gracefully — once you cross roughly **60% of the context window**, the model starts losing coherence. The industry calls it "lost in the middle": attention goes to the beginning (instructions) and the end (recent turns), but your actual working context in the middle gets progressively fuzzier.

I timed it over a week: **68 minutes per day** lost to re-orientation after compactions and new sessions.

> It's a **death spiral of diminishing context** — each compaction leaves the agent slightly dumber, which burns more tokens explaining things, which triggers the next compaction sooner.

### The Compaction Tax

Every 20–30 turns, the context warning hits and you get two bad choices: ignore it and watch the agent hallucinate, or run `/compact` and watch it lobotomize itself into a tidy two-paragraph summary of a 30-minute investigation. Either way you lose five minutes re-narrating your own project back to the agent like it's a new hire. That's not a workflow — that's a hamster wheel.

## The 200x ROI

Here's the cost comparison that made me build this:

| Operation | Tokens | What you get |
|-----------|--------|-------------|
| `grep -r "auth" src/` | ~5,000-10,000 | 500 results, mostly irrelevant |
| `find . -name "*.py"` | ~2,000 | Every Python file, no context |
| Agent re-orientation | ~2,000 | You re-explaining yesterday |
| **`auto-memory files --json --limit 10`** | **~50** | **Exactly the 10 files you touched yesterday** |

**50 tokens vs 10,000 — a 200x improvement.**

## Before & After

**Before auto-memory** — new session on a project:

```
You: Fix the failing test in the auth module

Agent: Let me explore the project structure...
       $ find . -name "*.py" | head -50           ← 2K tokens
       $ grep -r "test.*auth" tests/              ← 5K tokens
       $ cat tests/test_auth.py                    ← 3K tokens
       $ cat src/auth/handler.py                   ← 2K tokens
       I see several test files. Which test is failing?

You: The one we were working on yesterday, the token refresh edge case

Agent: Let me search for that...
       $ grep -r "refresh" tests/                  ← 4K tokens
       ...
```

Total: ~16K tokens burned, 8 minutes elapsed, agent still isn't oriented.

**After auto-memory** — same scenario:

```
You: Fix the failing test in the auth module

Agent: [auto-recall: auto-memory files --json --limit 10]
       → src/auth/refresh.py, tests/test_refresh_edge_cases.py,
         src/auth/token_store.py (last touched 14h ago)

       [auto-recall: auto-memory list --json --limit 3]
       → Yesterday: "Fixed token refresh race condition, one edge case
         test still failing on expired token + network timeout combo"

       I can see from your last session that test_refresh_edge_cases.py
       has a failing test for the expired token + network timeout case.
       Let me look at that specific test...
       $ cat tests/test_refresh_edge_cases.py      ← 1K tokens (targeted)
```

Total: ~1.1K tokens, 30 seconds, agent is immediately productive.

## How it compares

| Approach | Dependencies | Writes to DB | Setup | Agent-native |
|----------|-------------|-------------|-------|-------------|
| **auto-memory** | None (stdlib) | ❌ Read-only | `pip install` | ✅ Instruction-file |
| MCP server | Node.js runtime | Varies | Server config | ❌ Protocol layer |
| Custom hooks | Varies | Often yes | Hook scripts | ❌ Event-driven |
| Manual grep | None | ❌ | None | ❌ Manual |

## Mental Model: RAM vs Disk

- **Context window = RAM.** Fast, limited, clears on restart.
- **Agent's session store = Disk.** Persistent, searchable, grows forever — Copilot's `session-store.db` or Claude's JSONL transcripts.

auto-memory is the **page fault handler** — it pulls exact facts from disk in ~50 tokens when the agent needs them.

**It's not unlimited context. It's unlimited context *recall*.** In practice, same thing.

## Design

```
┌─────────────────────────────────────────────────────────────┐
│  agent instruction file (CLAUDE.md or copilot-instructions) │
│  "Run session-recall FIRST on every prompt"                 │
└─────────────────────┬───────────────────────────────────────┘
                      │ agent reads instruction
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  session-recall CLI  (pure Python, zero deps, read-only)    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ backends.detect()  →  copilot | claude                │  │
│  │ backend.ensure_index()   ← incremental (Claude only)  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────┬─────────────────────────┬─────────────┘
                      │                         │
        Copilot path  ▼                         ▼  Claude path
        ┌──────────────────────┐  ┌──────────────────────────┐
        │ ~/.copilot/          │  │ ~/.claude/projects/**.jsonl
        │   session-store.db   │  │              │           │
        │   (Copilot maintains)│  │              ▼           │
        │                      │  │ ingest/run.py            │
        │                      │  │              │           │
        │                      │  │              ▼           │
        │                      │  │ ~/.claude/               │
        │                      │  │   .session-recall.db     │
        │                      │  │   (Copilot-shaped + FTS5)│
        └──────────┬───────────┘  └──────────┬───────────────┘
                   │                         │
                   └────────────┬────────────┘
                                ▼
                   Read-only SQLite (sqlite3 + FTS5)
```

- **Zero runtime dependencies** — stdlib only (sqlite3, json, argparse)
- **Read-only** — Copilot's `session-store.db` is never written; Claude's JSONL transcripts are never modified
- **WAL-safe** — exponential backoff retry on `SQLITE_BUSY` (50→150→450 ms)
- **Schema-aware** — validates expected schema on every call, fails fast on drift
- **Incremental ingest** (Claude) — per-JSONL `(mtime, size)` checkpoint; back-to-back calls are near-no-ops
- **Telemetry** — ring buffer of last 500 invocations for concurrency monitoring

## Usage

### Try these prompts with your agent

 Once wired into your agent's instruction file, session-recall runs on every prompt — giving the agent your recent files and sessions as context before it does anything else.


```
"Search recent sessions about fixing the db connection bug"
"Check past 5 days sessions for latest plans?"
"Pick up where we left off on the API refactor"
"search recent sessions for last 10 files we modified"
"search sessions for the db migration bug"
```

No special syntax. The agent reads your session history and gets oriented in seconds instead of minutes.

### How it works under the hood

Progressive disclosure — most prompts never get past Tier 1.

**Tier 1 — Cheap scan (~50 tokens).** Usually enough.

```bash
session-recall files --json --limit 10
session-recall list --json --limit 5
```

**Tier 2 — Focused recall (~200 tokens).** When Tier 1 isn't enough.

```bash
session-recall search "specific term" --json
```

**Tier 3 — Full session detail (~500 tokens).** Only when investigating something specific.

```bash
session-recall show <session-id> --json
```

**Operational commands:**

```bash
session-recall health          # 10-dimension health dashboard
session-recall schema-check    # validate DB schema (after agent upgrades)
session-recall ingest --full   # Claude only: drop & rebuild index from JSONL
```

## Health Check

```
Dim Name                   Zone     Score  Detail
----------------------------------------------------------------------
 1  Freshness              🟢 GREEN  10.0  0.2h old
 2  Schema Integrity       🟢 GREEN  10.0  All tables/columns OK
 3  Query Latency          🟢 GREEN  10.0  1ms
 4  Corpus Size            🟢 GREEN  10.0  127 sessions
 5  Summary Coverage       🟢 GREEN   7.4  92% (117/127) (auto-derived)
 6  Repo Coverage          🟢 GREEN  10.0  8 sessions for owner/repo
 7  Concurrency            🟢 GREEN  10.0  busy=0.0%, p95=48ms
 8  E2E Probe              🟢 GREEN  10.0  list→show OK
 9  Progressive Disclosure ⚪ CALIBRATING  —  Collecting baseline (n=42/200)
 10 Index Ingest           🟢 GREEN  10.0  19 files indexed, 0.0m behind newest JSONL
```

The 10th dimension (`Index Ingest`) is Claude-only; on Copilot it reports `N/A` and is skipped from the overall score. On Windows consoles without UTF-8, glyphs gracefully fall back to ASCII tags (`[OK]`, `[--]`, `[!!]`, `[..]`, `[NA]`).

## Agent Integration

auto-memory works with **any agent that supports instruction files**. Installation wires `session-recall` into your agent's instruction file so it runs context recall automatically.

- **Claude Code** — append the block from [`claude-code-instructions-template.md`](claude-code-instructions-template.md) to `~/.claude/CLAUDE.md`. Optionally add a `SessionStart` hook from [`deploy/claude-code-hook.json`](deploy/claude-code-hook.json) for zero per-query latency.
- **Copilot CLI** — append the block from [`copilot-instructions-template.md`](copilot-instructions-template.md) to `~/.copilot/copilot-instructions.md`.
- See [`deploy/install.md`](deploy/install.md) for the full setup walkthrough.

After agent upgrades, validate the on-disk schema:
- Copilot CLI → [`UPGRADE-COPILOT-CLI.md`](UPGRADE-COPILOT-CLI.md)
- Claude Code → [`UPGRADE-CLAUDE-CODE.md`](UPGRADE-CLAUDE-CODE.md)

## What This Isn't

- **Not a vector database** — no embeddings, SQLite FTS5 only.
- **Not cross-machine sync** — local only.
- **Not a replacement for project documentation** — recalls *what you did*, not *how the system works*.

## FAQ

**Is it safe? Does it modify my session data?**
No. auto-memory is strictly read-only against the upstream stores. Copilot's `~/.copilot/session-store.db` is opened with `mode=ro` and never written. Claude's `~/.claude/projects/**/*.jsonl` files are only read — the SQLite *index* derived from them lives in a separate file (`~/.claude/.session-recall.db`).

**What happens when the upstream agent updates its schema?**
Run `session-recall schema-check` to validate. The tool fails fast on schema drift rather than returning bad data. See [UPGRADE-COPILOT-CLI.md](UPGRADE-COPILOT-CLI.md) and [UPGRADE-CLAUDE-CODE.md](UPGRADE-CLAUDE-CODE.md).

**Can I use both backends at the same time?**
Yes. With both stores present, `session-recall` defaults to Claude Code; pass `--backend copilot` to query Copilot specifically. Both wirings can coexist in their respective instruction files.

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and guidelines. Issues, PRs, and docs improvements are welcome.

⭐ **If auto-memory saved you time, [star the repo](https://github.com/dezgit2025/auto-memory)** — it's the best way to help others find it.

🔗 **Share it:** *"Zero-dependency CLI that gives your AI coding agent session memory. Read-only, schema-checked, ~50 tokens per prompt."* → [github.com/dezgit2025/auto-memory](https://github.com/dezgit2025/auto-memory)

## Disclaimer

This is an independent open-source project. It is **not** affiliated with, endorsed by, or supported by Microsoft, GitHub, Anthropic, or any other company. There is no official support — use at your own risk. Contributions and issues are welcome on GitHub.

## License

MIT
