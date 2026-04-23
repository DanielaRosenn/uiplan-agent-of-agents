param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repo

git config core.hooksPath .githooks | Out-Null

# Make the hooks executable on Unix-y shells (no-op on Windows/NTFS but
# git-bash / WSL users benefit).
if (Get-Command bash -ErrorAction SilentlyContinue) {
    bash -c "chmod +x .githooks/pre-commit .githooks/pre-push 2>/dev/null || true"
}

if (-not $Quiet) {
    Write-Host "Installed .githooks as git hooks path."
    Write-Host "Hooks will run 'python -m uipath_claude.skills.submodule_guard' before commit/push."
}
