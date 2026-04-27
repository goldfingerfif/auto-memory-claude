# Claude Code Upgrade Smoke Test

After every Claude Code upgrade, run these checks to verify `session-recall` still parses the JSONL transcript shape correctly.

## When to run

After any `claude` CLI upgrade (whether via `npm`, `brew`, or built-in updater).

## Steps

### 1. Record old version

```bash
claude --version
```

### 2. Capture a baseline ingest

```bash
session-recall --backend claude ingest --verbose | tail -3
session-recall --backend claude health --json | python3 -c "import sys,json; d=json.load(sys.stdin); print('overall:', d['overall_score'])"
```

Save the score; you'll compare after the upgrade.

### 3. Upgrade

Whatever you normally do. e.g. `claude` self-upgrade prompt, or your package manager.

### 4. Confirm new version

```bash
claude --version
```

### 5. Forced full rebuild

```bash
session-recall --backend claude ingest --full --verbose
```

If the ingestor sees a new JSONL field shape, malformed lines are skipped silently — they appear in the verbose output as `error parsing ...`. If the count of skipped lines is non-trivial, treat it as schema drift.

### 6. Schema check

```bash
session-recall --backend claude schema-check
```

Must exit 0. If not, the SQLite index didn't get the expected table shape; delete and rebuild:

```bash
rm ~/.claude/.session-recall.db
session-recall --backend claude ingest --full
session-recall --backend claude schema-check
```

### 7. Smoke test commands

```bash
session-recall --backend claude list --json --limit 3
session-recall --backend claude search "the" --json --limit 3
session-recall --backend claude show <one-id> --json
```

All three must return JSON without errors.

### 8. Health

```bash
session-recall --backend claude health --json
```

Index Ingest dim should be GREEN (0–5 minutes behind disk).

## If JSONL schema drifts

The reader at `src/session_recall/ingest/jsonl_reader.py` is intentionally tolerant — bad lines are skipped, not raised — so the ingest will keep working at reduced fidelity. Things you might need to update when Claude Code changes its line shape:

| Change | Where to look |
|---|---|
| New `type:"..."` value worth indexing | `src/session_recall/ingest/session_builder.py` |
| New tool name that touches files | `FILE_TOOLS` set in `session_builder.py` |
| `message.content[]` block shape change | `extract_text` / `extract_tool_uses` in `jsonl_reader.py` |
| Filename location moves out of `input.file_path` | `session_builder._record_file_touches` (search for `input.get("file_path")`) |
| Per-line metadata keys (`cwd`, `gitBranch`, `timestamp`) renamed | `session_builder.build()` field reads |

Open an issue if you hit drift in production — please include the offending JSONL line(s) (with sensitive content redacted).

## Known schema notes

| Claude Code version | Notes |
|---|---|
| 2.1.x | Initial supported version. `type` values: user, assistant, tool_use, tool_result, summary, system, plan_mode, attachment. File tools: Read, Write, Edit, NotebookEdit. |
