# Roadmap

This is the maintainer's checklist for this fork — what's done, what's queued.

## Shipped

- [x] GitHub Copilot CLI backend (initial release — reads `~/.copilot/session-store.db` read-only)
- [x] Claude Code backend (JSONL → SQLite index, auto-ingest, FTS5 search)
- [x] Backend abstraction with `--backend` flag and auto-detect (`backends.detect`)
- [x] CI on GitHub Actions (pytest + ruff matrix, Python 3.10–3.12, Ubuntu)
- [x] Schema-check command — fails fast on schema drift (exit 2)
- [x] 10-dimension health dashboard (Index Ingest is Claude-only)
- [x] Telemetry ring buffer (last 500 invocations) for concurrency monitoring
- [x] Windows console ASCII glyph fallback (`[OK]`, `[--]`, `[!!]`) when UTF-8 unavailable
- [x] Test suite — 138 collected tests passing
- [x] README accuracy pass — token counts measured under Claude Code (not just Copilot), text vs JSON costs documented honestly
- [x] "Tested on Claude Code" methodology section in README — re-runnable measurement command
- [x] Test badge updated to 138 (was 126)
- [x] Line-count subtitle updated to ~2,300 (was ~1,900)
- [x] Tier 1/2/3 documentation updated with measured costs (text ~120, JSON Tier-1 ~1,400, Tier-2 ~900, Tier-3 ~1,800)
- [x] ROI section recalibrated — honest 5–10× (JSON) / 40–80× (text) improvement, not the original 200× headline
- [x] Cold/warm ingest timing clarified (~5–20 ms warm / ~50–150 ms cold rebuild)
- [x] Health-check sample marked as illustrative ("your numbers will differ")
- [x] PII scrub for web publication — original author's GitHub-numeric-ID email removed from `pyproject.toml`; fork URLs point at `goldfingerfif/auto-memory-claude`
- [x] Original creator credited ([Desi Villanueva](https://github.com/dezgit2025)); fork maintainer line added to README
- [x] `.gitignore` already covers build artifacts (`*.egg-info/`), DBs, secrets, agent files (`.claude/`, `CLAUDE.md`)
- [x] Project-local Claude Code hooks for the fork (ruff lint on edit, pytest on edit, pyproject `dependencies` guard) — see `.claude/settings.json` (gitignored, fork-only)
- [x] Dev tooling installed for the fork (pyright-lsp, code-review, commit-commands, code-simplifier, claude-md-management, github MCP)

## Queued (next)

- [x] Fork URLs updated from placeholder to `goldfingerfif/auto-memory-claude`

## Not part of this fork 
- [ ] PyPI package publishing (`auto-memory` already named in `pyproject.toml`; needs a release workflow)
- [ ] `--brief` JSON output flag — drops `session_summary` to honor the original ~50-token claim with structured output
- [ ] Cursor backend
- [ ] OpenAI Codex backend
- [ ] Session diffing (what changed between sessions)
- [ ] Export sessions to markdown
- [ ] Optional MCP server wrapper for IDE integrations that don't support instruction files

## Out of scope (deliberately)

- Vector search / embeddings — SQLite FTS5 is the entire search story by design
- Cross-machine sync — local only; if you want sync, sync the underlying `.session-recall.db` yourself
- Replacing project documentation — recalls *what you did*, not *how the system works*

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
