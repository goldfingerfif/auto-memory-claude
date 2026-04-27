#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing session-recall..."

if command -v uv >/dev/null 2>&1; then
    echo "Using uv..."
    uv tool install --force --editable .
elif command -v pipx >/dev/null 2>&1; then
    echo "Using pipx..."
    pipx install --force -e .
else
    echo "WARN: uv and pipx not found, falling back to pip --user"
    python3 -m pip install --user --force-reinstall -e .
fi

echo ""
echo "Installed. Verify with:"
echo "  which session-recall"

# Detect agents and point user at the right next step
HAS_CLAUDE=0
HAS_COPILOT=0
[ -d "$HOME/.claude/projects" ] && HAS_CLAUDE=1
[ -f "$HOME/.copilot/session-store.db" ] && HAS_COPILOT=1

if [ "$HAS_CLAUDE" = "1" ] && [ "$HAS_COPILOT" = "1" ]; then
    echo "  session-recall list --json   # auto-detects (claude wins; --backend copilot overrides)"
elif [ "$HAS_CLAUDE" = "1" ]; then
    echo "  session-recall ingest --verbose"
    echo "  session-recall list --json"
    echo ""
    echo "Next: append the block from claude-code-instructions-template.md"
    echo "      to ~/.claude/CLAUDE.md so Claude Code runs recall on every prompt."
elif [ "$HAS_COPILOT" = "1" ]; then
    echo "  session-recall schema-check"
    echo "  session-recall list --json"
    echo ""
    echo "Next: append the block from copilot-instructions-template.md"
    echo "      to ~/.copilot/copilot-instructions.md."
else
    echo ""
    echo "Note: neither ~/.claude/projects/ nor ~/.copilot/session-store.db"
    echo "found. Run an agent session first, then re-run a smoke test:"
    echo "  session-recall list --json"
fi
