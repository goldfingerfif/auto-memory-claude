# Contributing to auto-memory

Thanks for your interest in contributing! Whether it's a bug fix, docs improvement, or new feature — all contributions are welcome.

## Quick Start

```bash
git clone https://github.com/goldfingerfif/auto-memory-claude.git
cd auto-memory-claude
pip install -e ".[dev]"
pytest src/session_recall/tests/ -q
```

## Good First Issues

Look for issues labeled [`good first issue`](https://github.com/goldfingerfif/auto-memory-claude/labels/good%20first%20issue) — these are scoped and beginner-friendly. Documentation fixes and typo corrections are always welcome too.

## Code Style (preferred, not enforced)

We prefer small, focused files:

- **≤80 lines per file** when practical
- **One function per file** (or a tightly coupled group of 2-3)
- **stdlib only** — no external runtime dependencies
- **Relative imports** within the package

These are guidelines, not gates. Don't let style concerns stop you from submitting a PR — we'll work through it together in review.

## Adding a Subcommand

1. Create `src/session_recall/commands/your_command.py` with `def run(args, backend=None) -> int`
2. Add argparse subparser in `__main__.py`
3. Add dispatch `elif` in `__main__.py` (pass `backend` through)
4. Add a `TIER_MAP` entry in `__main__.py`
5. Add tests in `tests/test_your_command.py`

## Adding a Health Dimension

1. Create `src/session_recall/health/dim_your_dim.py` with `def check(backend=None) -> dict`
2. Return `{"name", "score", "zone", "detail", "hint"}` — use `score=None, zone="N/A"` when the dim doesn't apply to the active backend
3. Import and add to `DIMS` list in `commands/health.py`

## Adding a Backend

session-recall supports multiple session-store backends behind a small interface. To add one (e.g. Cursor, Codex):

1. Create `src/session_recall/backends/your_backend.py` exposing `def build() -> Backend`
2. Register it in `src/session_recall/backends/__init__.py` (`REGISTRY` dict + an `_xxx_present()` detector)
3. If the upstream tool doesn't already maintain a SQLite store, write an ingestor under `src/session_recall/ingest/` that produces a Copilot-shaped DB (see `backends/claude_code.py` and `ingest/run.py` as the reference example)
4. Add tests under `tests/` with fixture data — no live agent dependency
5. Document setup in `deploy/install.md`

## PR Checklist

Before submitting:

- [ ] Tests pass: `pytest src/session_recall/tests/ -q`
- [ ] Lint passes: `ruff check src/`
- [ ] No new runtime dependencies added
- [ ] Docs updated if behavior changed

## Questions?

Open an issue or start a discussion — happy to help.
