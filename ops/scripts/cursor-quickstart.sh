#!/usr/bin/env bash
# One-shot Cursor + MCP setup after clone (minimal manual steps).
# Requires: git, uv (https://docs.astral.sh/uv/). Run from repo root:
#   bash ops/scripts/cursor-quickstart.sh

set -euo pipefail
FORCE=0
if [[ "${1:-}" == "--force" || "${1:-}" == "-f" ]]; then
  FORCE=1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$REPO_ROOT"

echo "== Cursor quickstart (repo: $REPO_ROOT) =="

CHOICE_FILE="$REPO_ROOT/.assistant-choice"
CHOICE="cursor"
if [[ -f "$CHOICE_FILE" ]]; then
  EXISTING="$(tr -d '[:space:]' < "$CHOICE_FILE" | tr '[:upper:]' '[:lower:]')"
  if [[ -n "$EXISTING" && "$EXISTING" != "$CHOICE" && $FORCE -ne 1 ]]; then
    echo "This clone is currently configured for '$EXISTING'." >&2
    echo "To switch to Cursor, re-run with --force." >&2
    exit 1
  fi
fi
printf "%s" "$CHOICE" > "$CHOICE_FILE"
echo "Assistant choice for this clone: $CHOICE"

command -v git >/dev/null || { echo "git is required on PATH." >&2; exit 1; }

git submodule update --init --recursive

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install from https://docs.astral.sh/uv/ then re-run." >&2
  echo 'Fallback: pip install -e ".[mcp]" and copy .cursor/mcp.json.example to .cursor/mcp.json' >&2
  exit 1
fi

echo "uv sync --extra mcp ..."
uv sync --extra mcp

mkdir -p "$REPO_ROOT/.cursor"
if [[ ! -f "$REPO_ROOT/.cursor/mcp.json" ]]; then
  if [[ ! -f "$REPO_ROOT/.cursor/mcp.json.example" ]]; then
    echo "Missing .cursor/mcp.json.example" >&2
    exit 1
  fi
  cp "$REPO_ROOT/.cursor/mcp.json.example" "$REPO_ROOT/.cursor/mcp.json"
  echo "Created .cursor/mcp.json from mcp.json.example"
else
  echo ".cursor/mcp.json already exists (left unchanged)."
fi

if [[ $FORCE -eq 1 ]]; then
  bash "$SCRIPT_DIR/setup-cursor.sh" --force
else
  bash "$SCRIPT_DIR/setup-cursor.sh"
fi

echo ""
echo "Next (human, ~30 seconds):"
echo "  1. File -> Open Folder -> this repo root"
echo "  2. Cursor: Settings -> MCP -> confirm uipath-builder-agent is green"
echo "  3. Command Palette -> Developer: Reload Window (if MCP was red)"
echo ""
echo "Optional: cursor-public/superpowers — see docs/CURSOR_USER_GUIDE.md"
