#!/bin/bash
# Setup Cursor skills for UiPath Builder Agent
# Run this script after cloning to enable Cursor skill discovery

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CURSOR_SKILLS_DIR="$REPO_ROOT/.cursor/skills"
SOURCE_SKILLS_DIR="$REPO_ROOT/skills/skills"

echo "Setting up Cursor skills..."

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
    if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
        echo "Removing existing .cursor/skills..."
        rm -rf "$CURSOR_SKILLS_DIR"
    else
        echo ".cursor/skills already exists. Use --force to recreate."
        exit 0
    fi
fi

# Create symlink
ln -s "../skills/skills" "$CURSOR_SKILLS_DIR"
echo "Created symlink: .cursor/skills -> skills/skills"

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
echo "For UiPath CLI integration (validation, execution, packages):"
echo '  pip install -e ".[mcp]"'
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
