#!/usr/bin/env bash
# One-shot Claude CLI setup after clone (minimal manual steps).
# Requires: git, uv (https://docs.astral.sh/uv/). Run from repo root:
#   bash ops/scripts/claude-quickstart.sh

set -euo pipefail
FORCE=0
if [[ "${1:-}" == "--force" || "${1:-}" == "-f" ]]; then
  FORCE=1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$REPO_ROOT"

echo "== Claude quickstart (repo: $REPO_ROOT) =="

CHOICE_FILE="$REPO_ROOT/.assistant-choice"
CHOICE="claude"
if [[ -f "$CHOICE_FILE" ]]; then
  EXISTING="$(tr -d '[:space:]' < "$CHOICE_FILE" | tr '[:upper:]' '[:lower:]')"
  if [[ -n "$EXISTING" && "$EXISTING" != "$CHOICE" && $FORCE -ne 1 ]]; then
    echo "This clone is currently configured for '$EXISTING'." >&2
    echo "To switch to Claude, re-run with --force." >&2
    exit 1
  fi
fi
printf "%s" "$CHOICE" > "$CHOICE_FILE"
echo "Assistant choice for this clone: $CHOICE"

command -v git >/dev/null || { echo "git is required on PATH." >&2; exit 1; }
git submodule update --init --recursive

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install from https://docs.astral.sh/uv/ then re-run." >&2
  echo 'Fallback: pip install -e ".[dev]"' >&2
  exit 1
fi

echo "uv sync --extra dev ..."
uv sync --extra dev

echo ""
echo "Next (human, ~30 seconds):"
echo "  1. Run: uipath-claude chat"
echo "  2. Run /status and /skills in chat"
echo "  3. If Bedrock auth fails, run: aws sts get-caller-identity"
