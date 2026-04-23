#!/usr/bin/env bash
# One-click update for the UiPath/skills submodule (mac/linux twin).
# Usage:
#   ops/scripts/update-skills.sh            # pull + print diff
#   ops/scripts/update-skills.sh --check    # dry-run: exits 0 up-to-date, 2 updates available
#   ops/scripts/update-skills.sh --commit   # pull + print diff + commit submodule bump

set -e
mode="update"
for arg in "$@"; do
    case "$arg" in
        --check) mode="check" ;;
        --commit) mode="commit" ;;
        *) echo "unknown arg: $arg" >&2; exit 64 ;;
    esac
done

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

if [ "$mode" = "check" ]; then
    python3 -c '
from uipath_claude.skills.updater import check_for_updates
has, msg, cur, rem = check_for_updates()
print(msg)
raise SystemExit(2 if has else 0)
'
    exit $?
fi

python3 -c '
from uipath_claude.skills.updater import update_skills
ok, msg = update_skills()
print(msg)
raise SystemExit(0 if ok else 1)
'

python3 -c 'from uipath_claude.skills.upstream_scan import scan_upstream, format_diff; print(format_diff(scan_upstream()))'

if [ "$mode" = "commit" ]; then
    git add skills
    if ! git diff --cached --quiet -- skills; then
        sha=$(git -C skills rev-parse --short HEAD)
        git commit -m "chore: bump skills submodule to $sha"
    else
        echo "No submodule change to commit."
    fi
fi
