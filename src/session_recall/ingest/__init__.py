"""Claude Code JSONL → SQLite ingestor.

Reads ~/.claude/projects/**/*.jsonl and writes a Copilot-shaped SQLite index
(plus an FTS5 search_index virtual table). Idempotent and incremental:
re-running with no JSONL changes is a near-no-op (each file's mtime + size
are checkpointed in the _ingest_state table).
"""
