#!/usr/bin/env bash
# Cursor sessionStart hook (mac/linux twin of check-skills-update.ps1).
# Throttles the check to once per THROTTLE_DAYS. Fail-open on any error.

set -e
THROTTLE_DAYS=2

emit_empty() { printf '{}\n'; exit 0; }
emit_banner() {
    python3 -c "import json,sys; print(json.dumps({'additional_context': sys.argv[1]}))" "$1"
    exit 0
}

{
    script_dir="$(cd "$(dirname "$0")" && pwd)"
    repo_root="$(cd "$script_dir/../.." && pwd)"
    state_dir="$repo_root/.cursor/hooks/state"
    stamp="$state_dir/last-update-check"

    mkdir -p "$state_dir"
    now=$(date +%s)
    last=0
    [ -f "$stamp" ] && last=$(cat "$stamp" 2>/dev/null || echo 0)
    throttle=$((THROTTLE_DAYS * 24 * 60 * 60))
    if [ $((now - last)) -lt "$throttle" ]; then emit_empty; fi

    printf '%s' "$now" > "$stamp"

    out=$(cd "$repo_root" && python3 -c '
from uipath_claude.skills.updater import check_for_updates
has, msg, cur, rem = check_for_updates()
print("HAS_UPDATES" if has else "UP_TO_DATE")
print(msg)
' 2>/dev/null) || emit_empty

    first_line=$(printf '%s' "$out" | head -n1)
    if [ "$first_line" != "HAS_UPDATES" ]; then emit_empty; fi

    detail=$(printf '%s' "$out" | tail -n +2 | tr '\n' ' ' | sed 's/[[:space:]]*$//')
    banner="UiPath skills submodule has updates available (${detail}). Run /update-skills in chat, or scripts/update-skills.sh from a shell."
    emit_banner "$banner"
} || emit_empty
