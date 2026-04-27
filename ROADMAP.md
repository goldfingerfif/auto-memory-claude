# Roadmap

Planned work for auto-memory. Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Shipped

- [x] GitHub Copilot CLI backend (initial release)
- [x] Claude Code backend (JSONL → SQLite index, auto-ingest, FTS5 search)
- [x] Backend abstraction with `--backend` flag and auto-detect
- [x] CI with GitHub Actions (pytest + ruff matrix, Python 3.10–3.12)

## Planned

- [ ] PyPI package publishing
- [ ] Cursor backend
- [ ] OpenAI Codex backend
- [ ] Session diffing (what changed between sessions)
- [ ] Export sessions to markdown
- [ ] Optional MCP server wrapper for IDE integration
- [ ] Richer health dimensions (token usage, context efficiency)
