# One-click update for the UiPath/skills submodule.
# Usage:
#   ops/scripts/update-skills.ps1           # pull + print diff
#   ops/scripts/update-skills.ps1 -Check    # dry-run: exits 0 up-to-date, 2 updates available
#   ops/scripts/update-skills.ps1 -Commit   # pull + print diff + commit submodule bump

param([switch]$Check, [switch]$Commit)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    if ($Check) {
        $py = @'
from uipath_claude.skills.updater import check_for_updates
has, msg, cur, rem = check_for_updates()
print(msg)
raise SystemExit(2 if has else 0)
'@
        python -c $py
        exit $LASTEXITCODE
    }

    $py = @'
from uipath_claude.skills.updater import update_skills
ok, msg = update_skills()
print(msg)
raise SystemExit(0 if ok else 1)
'@
    python -c $py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    python -c "from uipath_claude.skills.upstream_scan import scan_upstream, format_diff; print(format_diff(scan_upstream()))"

    if ($Commit) {
        git add skills
        git diff --cached --quiet -- skills
        if ($LASTEXITCODE -ne 0) {
            $sha = (git -C skills rev-parse --short HEAD).Trim()
            git commit -m "chore: bump skills submodule to $sha"
        } else {
            Write-Host "No submodule change to commit."
        }
    }
}
finally {
    Pop-Location
}
