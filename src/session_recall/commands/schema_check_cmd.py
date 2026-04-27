"""Schema-check subcommand — validates session-store DB structure."""
import sys
from ..config import DB_PATH
from ..db.connect import connect_ro
from ..db.schema_check import schema_check
from ..util.format_output import fmt_json


def run(args, backend=None) -> int:
    """Execute schema-check. Returns 0 if OK, 2 if drift."""
    db_path = backend.db_path if backend is not None else DB_PATH
    expected = backend.expected_schema if backend is not None else None
    conn = connect_ro(db_path)
    problems = schema_check(conn, expected)
    conn.close()
    json_mode = getattr(args, "json", False)
    if problems:
        if json_mode:
            print(fmt_json({"ok": False, "problems": problems}))
        else:
            agent = backend.name if backend is not None else "copilot"
            print(f"❌ Schema drift on {agent} backend.", file=sys.stderr)
            for p in problems:
                print(f"   - {p}", file=sys.stderr)
        return 2
    print(fmt_json({"ok": True, "problems": []}) if json_mode else "✅ Schema OK")
    return 0
