# Cursor sessionStart hook: check UiPath/skills submodule for updates at most
# once per THROTTLE_DAYS. Surfaces a banner in the new chat via additional_context.
#
# Contract (Cursor hooks): emit a single JSON object on stdout. Fail-open on any
# error so offline / broken setups never block a session.
#
# Team-shared: committed under .cursor/hooks/. Per-user stamp lives under
# .cursor/hooks/state/ which is gitignored.

$ErrorActionPreference = "Stop"
$ThrottleDays = 2

function Emit-Empty {
    '{}' | Write-Output
    exit 0
}

function Emit-Banner($message) {
    $payload = @{ additional_context = $message } | ConvertTo-Json -Compress
    $payload | Write-Output
    exit 0
}

try {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    $stateDir = Join-Path $repoRoot ".cursor\hooks\state"
    $stamp    = Join-Path $stateDir "last-update-check"

    if (-not (Test-Path $stateDir)) {
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    }

    $now = [int][double]::Parse((Get-Date -UFormat %s))
    $last = 0
    if (Test-Path $stamp) {
        try { $last = [int](Get-Content $stamp -Raw).Trim() } catch { $last = 0 }
    }

    $throttleSec = $ThrottleDays * 24 * 60 * 60
    if (($now - $last) -lt $throttleSec) {
        Emit-Empty
    }

    Set-Content -Path $stamp -Value $now -NoNewline

    $py = @'
from uipath_claude.skills.updater import check_for_updates
has, msg, cur, rem = check_for_updates()
print("HAS_UPDATES" if has else "UP_TO_DATE")
print(msg)
'@
    Push-Location $repoRoot
    try {
        $out = python -c $py 2>$null
    } finally {
        Pop-Location
    }

    if (-not $out) { Emit-Empty }
    $lines = $out -split "`n"
    if ($lines[0].Trim() -ne "HAS_UPDATES") { Emit-Empty }

    $detail = ($lines[1..($lines.Length-1)] -join " ").Trim()
    $banner = "UiPath skills submodule has updates available ($detail). " +
              "Run /update-skills in chat, or ops/scripts/update-skills.ps1 -Commit from a shell."
    Emit-Banner $banner
}
catch {
    Emit-Empty
}
