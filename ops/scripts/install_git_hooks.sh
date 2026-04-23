#!/usr/bin/env bash
# Install the repo-local git hooks for the UiPath submodule guard.
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/pre-push 2>/dev/null || true

echo "Installed .githooks as git hooks path."
echo "Hooks will run 'python -m uipath_claude.skills.submodule_guard' before commit/push."
