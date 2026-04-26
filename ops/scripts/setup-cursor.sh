#!/bin/bash
# Setup Cursor skills for UiPath Builder Agent
# Run this script after cloning to enable Cursor skill discovery

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Script lives at <repo>/ops/scripts/ — repo root is two levels up
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CURSOR_SKILLS_DIR="$REPO_ROOT/.cursor/skills"
SOURCE_SKILLS_DIR="$REPO_ROOT/skills/skills"
OVERLAY_SKILLS_DIR="$REPO_ROOT/extensions/skills"
FORCE=0
if [ "${1:-}" = "--force" ] || [ "${1:-}" = "-f" ]; then
    FORCE=1
fi

echo "Setting up Cursor skills..."

CHOICE_FILE="$REPO_ROOT/.assistant-choice"
CHOICE="cursor"
if [ -f "$CHOICE_FILE" ]; then
    EXISTING="$(tr -d '[:space:]' < "$CHOICE_FILE" | tr '[:upper:]' '[:lower:]')"
    if [ -n "$EXISTING" ] && [ "$EXISTING" != "$CHOICE" ] && [ "$FORCE" -ne 1 ]; then
        echo "This clone is currently configured for '$EXISTING'." >&2
        echo "To switch to Cursor, re-run with --force." >&2
        exit 1
    fi
fi
printf "%s" "$CHOICE" > "$CHOICE_FILE"
echo "Assistant choice for this clone: $CHOICE"

# Check if source skills exist
if [ ! -d "$SOURCE_SKILLS_DIR" ]; then
    echo "Error: skills/skills directory not found."
    echo "Run: git submodule update --init --recursive"
    exit 1
fi

# Create .cursor directory if needed
mkdir -p "$REPO_ROOT/.cursor"

# Check if skills directory already exists
if [ -e "$CURSOR_SKILLS_DIR" ]; then
    if [ "$FORCE" -eq 1 ]; then
        echo "Removing existing .cursor/skills..."
        rm -rf "$CURSOR_SKILLS_DIR"
    else
        echo ".cursor/skills already exists. Use --force to recreate."
        exit 0
    fi
fi

# Build a generated physical view. This preserves local Cursor overlays
# (uiplan, mermaid guidance, legacy redirects) while keeping skills/skills
# as the official upstream source of truth.
mkdir -p "$CURSOR_SKILLS_DIR"
cp -R "$SOURCE_SKILLS_DIR"/. "$CURSOR_SKILLS_DIR"/
if [ -d "$OVERLAY_SKILLS_DIR" ]; then
    for skill in "$OVERLAY_SKILLS_DIR"/*/; do
        [ -d "$skill" ] || continue
        cp -R "$skill" "$CURSOR_SKILLS_DIR"/
    done
fi
echo "Generated .cursor/skills from skills/skills plus extensions/skills overlays"
echo "Re-run this script after pulling changes or advancing the skills submodule."

echo ""
echo "Cursor setup complete!"
echo ""
echo "Available UiPath skills:"
for skill in "$CURSOR_SKILLS_DIR"/*/; do
    echo "  - $(basename "$skill")"
done
echo ""
echo "========================================"
echo "STEP 2: Install MCP Tools (Optional)"
echo "========================================"
echo ""
echo "Python deps (if not already done):"
echo '  uv sync --extra mcp   OR   pip install -e ".[mcp]"'
echo "  Or: bash ops/scripts/cursor-quickstart.sh"
echo ""
echo "MCP config is at: .cursor/mcp.json"
echo "Cursor will auto-detect it when you open the folder."
echo ""
echo "========================================"
echo "STEP 3: Install Superpowers Plugin"
echo "========================================"
echo ""
echo "Add to Cursor settings.json:"
echo '  "cursor.plugins": ["cursor-public/superpowers"]'
echo ""
echo "Superpowers adds:"
echo "  - brainstorming      (design before code)"
echo "  - writing-plans      (implementation plans)"
echo "  - executing-plans    (task-by-task execution)"
echo "  - test-driven-dev    (TDD workflow)"
echo "  - systematic-debug   (bug investigation)"
echo "  - code-review        (quality checks)"
echo ""
echo "See docs/CURSOR_USER_GUIDE.md for full documentation."
echo ""
echo "Open this folder in Cursor to start building UiPath workflows."
