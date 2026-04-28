"""Dim 6: Repo coverage — sessions exist for the current working directory.

Three-step waterfall so the dim still scores well in non-git checkouts
(the Claude backend stores cwd per session, so we have a path even when
`git remote get-url origin` fails):

  1. git remote → owner/repo  → SELECT WHERE repository = ?
  2. CWD basename             → SELECT WHERE repository = basename(cwd)
  3. CWD path equality/prefix → SELECT WHERE cwd = ? OR cwd LIKE ?

Stays RED only if all three find zero rows.
"""
import os
from pathlib import Path

from ..db.connect import connect_ro
from ..config import DB_PATH
from ..util.detect_repo import detect_repo

HINT = "Run in a git repo or pass --repo all"


def check(backend=None) -> dict:
    db_path = backend.db_path if backend is not None else DB_PATH
    cwd = os.getcwd()
    cwd_base = Path(cwd).name

    try:
        conn = connect_ro(db_path)
    except Exception as e:
        return {"name": "Repo Coverage", "score": 0, "zone": "RED",
                "detail": str(e), "hint": HINT}

    try:
        # Step 1: git remote
        repo = detect_repo()
        if repo:
            count = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE repository = ?", (repo,)
            ).fetchone()[0]
            if count >= 1:
                conn.close()
                return {"name": "Repo Coverage", "score": 10, "zone": "GREEN",
                        "detail": f"{count} sessions for {repo}", "hint": ""}

        # Step 2: cwd basename (matches the ingest fallback that stores
        # Path(cwd).name as repository when git remote isn't available)
        if cwd_base:
            count = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE repository = ?", (cwd_base,)
            ).fetchone()[0]
            if count >= 1:
                conn.close()
                return {"name": "Repo Coverage", "score": 10, "zone": "GREEN",
                        "detail": f"{count} sessions for cwd:{cwd_base}",
                        "hint": ""}

        # Step 3: cwd path equality or sub-path. JSONL transcripts may use
        # either separator (Windows backslashes or Unix forward slashes), so
        # check both LIKE patterns.
        cwd_stripped = cwd.rstrip("/\\")
        like_fwd = cwd_stripped + "/%"
        like_bwd = cwd_stripped + "\\%"
        count = conn.execute(
            "SELECT COUNT(*) FROM sessions "
            "WHERE cwd = ? OR cwd LIKE ? OR cwd LIKE ?",
            (cwd, like_fwd, like_bwd),
        ).fetchone()[0]
        if count >= 1:
            conn.close()
            label = cwd_base or cwd
            return {"name": "Repo Coverage", "score": 10, "zone": "GREEN",
                    "detail": f"{count} sessions for cwd:{label}", "hint": ""}

        conn.close()
    except Exception as e:
        conn.close()
        return {"name": "Repo Coverage", "score": 0, "zone": "RED",
                "detail": str(e), "hint": HINT}

    label = repo or cwd_base or cwd
    return {"name": "Repo Coverage", "score": 5, "zone": "AMBER",
            "detail": f"0 sessions for {label}", "hint": HINT}
