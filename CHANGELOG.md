# Changelog

All notable changes to `auto-memory` (CLI: `session-recall`) are documented here. This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-04-28

Fork release. Adds Claude Code as a first-class backend alongside the original GitHub Copilot CLI support, plus measured-honest token claims and a `--brief` flag for cheap structured recall.

### Added
- **Claude Code backend** — reads `~/.claude/projects/**/*.jsonl` and ingests into a local SQLite index at `~/.claude/.session-recall.db`. Incremental on every CLI call (~5–20 ms warm, ~50–150 ms cold rebuild). Mirrors the Copilot schema so the entire query layer is shared.
- **Backend abstraction** — `--backend` flag and `SESSION_RECALL_BACKEND` env var. Auto-detects when both Claude and Copilot indexes are present (Claude wins by default).
- **`--brief` flag** for `list`, `files`, `search`, `show`, and `checkpoints`. Drops the `session_summary` / `summary` fields under `--json` for ~30–50% smaller output. Plain-text mode is unaffected.
- **Schema-check command** — fails fast on schema drift (exit 2).
- **10-dimension health dashboard** with telemetry ring buffer (last 500 invocations).
- **Windows console ASCII glyph fallback** (`[OK]`, `[--]`, `[!!]`) when UTF-8 is unavailable.
- 12 new tests covering `--brief`, plus expansion of the existing suite to 150 collected tests.
- `CHANGELOG.md`, `ROADMAP.md` (fork roadmap), `UPGRADE-CLAUDE-CODE.md`.

### Changed
- Documentation re-measured against Claude Code: Tier 1 plain text ~120 tokens, Tier 1 `--json` ~1,400, Tier 1 `--json --brief` ~700, Tier 2 ~600–900, Tier 3 ~1,800.
- Honest ROI framing: 5–10× (JSON) or 40–80× (plain text) vs. blind grep, instead of the original 200× headline.
- `pyproject.toml` URLs and maintainer fields point at the fork (`goldfingerfif/auto-memory-claude`); original creator credit preserved.

### Fixed
- Ruff lint clean: F841 (unused `last_err` in `db/connect.py` — now chained via `from`), F401 × 4 (unused imports in test files), F841 × 2 (unused `code = run(args)` assignments), E401 × 1 (`import json, time` split).
- Untracked `__pycache__/` and `auto_memory.egg-info/` from the repo (they were committed before the gitignore covered them).
- `.gitignore` no longer blocks `CHANGELOG.md`.
- `[tool.ruff.lint]` config now permits the project's intentional compact one-line style in `types.py` and `util/telemetry.py` (E701/E702 ignored — see CONTRIBUTING.md "≤80 lines/file" guidance).

### Constraint preserved
- **stdlib-only** (`dependencies = []`). The runtime adds zero PyPI dependencies.

## [0.1.0] — 2024–2025

Original release by [Desi Villanueva](https://github.com/dezgit2025). Progressive session recall for GitHub Copilot CLI, reading `~/.copilot/session-store.db` via read-only SQLite + FTS5.

[0.2.0]: https://github.com/goldfingerfif/auto-memory-claude/releases/tag/v0.2.0
[0.1.0]: https://github.com/goldfingerfif/auto-memory-claude/releases/tag/v0.1.0
