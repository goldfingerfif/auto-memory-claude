"""Detect current repository from git remote or environment."""
import subprocess
import re


def detect_repo(cwd: str | None = None) -> str | None:
    """Return 'owner/repo' from git remote origin, or None.

    `cwd` lets the ingestor resolve a session's repository from the JSONL's
    cwd field rather than the CLI's current directory.
    """
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        ).stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError, OSError):
        return None
    if not url:
        return None
    # Handle SSH: git@github.com:owner/repo.git
    m = re.match(r"git@[^:]+:(.+?)(?:\.git)?$", url)
    if m:
        return m.group(1)
    # Handle HTTPS: https://github.com/owner/repo.git
    m = re.match(r"https?://[^/]+/(.+?)(?:\.git)?$", url)
    if m:
        return m.group(1)
    return None
