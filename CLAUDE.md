# CLAUDE.md

This file provides persistent guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`auto-memory` (CLI binary: `session-recall`) is a zero-dependency Python CLI that gives any AI coding agent instant, low-token progressive recall of recent sessions, files, checkpoints, and summaries (~50–150 tokens for Tier 1 plain text, ~1,400 with `--json`).

It functions as a **page fault handler** for the agent's context window:
- Context window = volatile RAM
- agent's session store = persistent disk
- `session-recall` = lightweight recall mechanism

It supports two backends today, selected via `--backend` or auto-detect:

| Backend | Reads | Maintained by |
|---|---|---|
| `copilot` | `~/.copilot/session-store.db` (SQLite + FTS5) | Copilot CLI itself; we read it `mode=ro` |
| `claude` | `~/.claude/projects/**/*.jsonl` → ingested into `~/.claude/.session-recall.db` | Our `ingest/` module; incremental on every CLI call |

The Claude index mirrors the Copilot schema exactly so the entire query layer (`commands/*.py`, `db/schema_check.py`, FTS5 search, 9 of 10 health dims) is shared without modification.

## Commands

```bash
pip install -e ".[dev]"             # install with dev extras (pytest, ruff)
pytest src/session_recall/tests/ -q # full test suite (CI runs `pytest src/ -q`)
pytest src/session_recall/tests/test_list_sessions.py -q   # single file
pytest src/ -k test_health_scoring -q                       # single test by name
ruff check src/                     # lint (CI gate)
session-recall <command> --json     # run the CLI after install
session-recall --backend claude ingest --verbose      # rebuild the Claude index
SESSION_RECALL_DB=/tmp/test.db session-recall list    # point at a fixture DB
```

CI matrix: Python 3.10 / 3.11 / 3.12 on Ubuntu (`.github/workflows/test.yml`). Both `ruff check src/` and `pytest src/ -q` must pass.

## Architecture

### Backend abstraction (`backends/`)

`backends.detect(explicit) -> Backend` resolves the active backend with this precedence: explicit `--backend` flag → `SESSION_RECALL_BACKEND` env var → presence check (`~/.claude/projects/`, `~/.copilot/session-store.db`). When both are present, Claude wins by default and a one-line note goes to stderr.

A `Backend` is a small dataclass: `name`, `db_path`, `instructions_path`, `expected_schema`, `ensure_index()`, `freshness_signal()`. Copilot's `ensure_index` is a no-op; Claude's runs the incremental ingestor.

### Command dispatch flow (`__main__.py`)

`__main__` parses args, calls `backends.detect(args.backend)`, runs `backend.ensure_index()` (no-op on Copilot, incremental ingest on Claude), then lazy-imports the matching `commands/<cmd>.py` and calls `run(args, backend) -> int`. Telemetry is recorded after the call (duration, tier from `TIER_MAP`, optional `query_hash`/`session_id_prefix`). Tiers: 0 = meta/ops (`health`, `schema-check`, `ingest`), 1 = cheap scan (`list`, `files`, `checkpoints`), 2 = focused (`search`), 3 = deep (`show`).

### Read path (commands)

Each `commands/*.py` opens a read-only SQLite connection via `db/connect.connect_ro` (with `PRAGMA query_only=ON` and `[50,150,450] ms` jittered retry on `SQLITE_BUSY`), validates schema via `db/schema_check.schema_check(conn, backend.expected_schema)` and exits 2 on drift, then issues plain SQL. Output goes through `util/format_output.output` (text or JSON via `--json`). `--days N` is implemented as a `datetime('now', '-N days')` predicate; default windows differ per command (`list` defaults to 30 days).

Each command keeps a module-level `from ..config import DB_PATH` import as a legacy fallback when `backend=None` (some tests patch this symbol directly).

### Ingest path (`ingest/`, Claude only)

`ingest/run.py:run_incremental(db_path, projects_dir)` walks `~/.claude/projects/*/` and for each `.jsonl`:
1. Compares `(mtime_ns, byte_size)` against the `_ingest_state` row → skip if unchanged.
2. If grown: load prior `SessionRows` from the DB, parse only lines past `last_line_count`, append.
3. If shrunk or new: full re-ingest of that one session (DELETE + INSERT in a transaction).

The line walker (`ingest/jsonl_reader.py`) is intentionally tolerant — malformed JSON lines are skipped rather than raising. The session builder (`ingest/session_builder.py`) maps Claude's record `type` values (`user`, `assistant`, `tool_use`, `plan_mode`, `summary`) onto the Copilot tables. The Copilot-shape schema lives in `ingest/schema.py:SCHEMA_SQL`.

The first `type:"user"` text becomes the derived `summary` (prefixed `~` so dim_summary_coverage can annotate "auto-derived"). Slash-command preambles (`<command-message>`, `<local-command-caveat>`, …) are stripped before snipping. Tool uses with `name in {Read, Write, Edit, NotebookEdit}` populate `session_files`. `type:"plan_mode"` events become `checkpoints`.

When upstream JSONL shape drifts, follow `UPGRADE-CLAUDE-CODE.md`. The fallback drop-and-rebuild is `session-recall --backend claude ingest --full`.

### Health subsystem (`health/`)

`commands/health.py` orchestrates 10 dimensions (`dim_freshness`, `dim_schema`, `dim_latency`, `dim_corpus`, `dim_summary_coverage`, `dim_repo_coverage`, `dim_concurrency`, `dim_e2e`, `dim_disclosure`, `dim_ingest`). Each exposes `check(backend=None) -> {name, score, zone, detail, hint}`. Dims that don't apply to the active backend return `score=None, zone="N/A"` and are skipped by `health/scoring.overall_score()` (which takes `min()` of scored dims). `dim_ingest` is N/A on Copilot. `dim_freshness` reads `backend.freshness_signal()` so on Claude it tracks the newest JSONL mtime, not the local index file.

### Telemetry (`util/telemetry.py`)

JSON ring buffer (last 500 entries) at `$SESSION_RECALL_TELEMETRY` (default `~/.copilot/scripts/.session-recall-stats.json` for legacy continuity — same file is reused across backends). `record()` is wrapped in a bare `except: pass` — telemetry must never crash the CLI. New optional fields are appended only when non-None, preserving backward compatibility with older entries. `dim_concurrency` and `dim_disclosure` read this buffer.

### Configuration

Env-overridable paths:
- `SESSION_RECALL_DB` → DB path (Copilot or Claude index)
- `SESSION_RECALL_CLAUDE_PROJECTS` → Claude projects dir
- `SESSION_RECALL_TELEMETRY` → telemetry buffer path
- `SESSION_RECALL_BACKEND` → force `copilot` or `claude` without the flag
- `EXPECTED_SCHEMA_VERSION` is currently `1`; bump when `EXPECTED_SCHEMA` changes meaningfully.

## Conventions (from CONTRIBUTING.md)

- **stdlib only** — never add a runtime dependency. `pyproject.toml` declares `dependencies = []` and that is load-bearing for the project's identity.
- **Read-only against upstream** — never `INSERT`/`UPDATE`/`DELETE` against `session-store.db`. Never modify Claude JSONL files. The Claude *index* is ours to write, but it lives at a separate path (`~/.claude/.session-recall.db`).
- Prefer **≤80 lines/file** and **one function per file** (or a small tightly coupled group). Use **relative imports** within the package.
- Adding a subcommand: create `commands/<cmd>.py` with `run(args, backend=None) -> int`, register a subparser + dispatch `elif` in `__main__.py`, add a `TIER_MAP` entry, add tests under `tests/test_<cmd>.py`.
- Adding a backend: create `backends/<name>.py` with a `build() -> Backend`, register in `backends/__init__.py:REGISTRY`, add a presence detector. If upstream isn't already a SQLite store, add an ingestor under `ingest/`.

## Exit codes

- `0` success
- `1` generic error / no subcommand
- `2` schema drift (tests assert this — don't change without updating call sites)
- `3` DB locked after retries
- `4` DB file missing
