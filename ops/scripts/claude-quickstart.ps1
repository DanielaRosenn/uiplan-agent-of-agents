# One-shot Claude CLI setup after clone (minimal manual steps).
# Requires: git, uv (https://docs.astral.sh/uv/). Run from anywhere.
#
#   pwsh -File ops/scripts/claude-quickstart.ps1
# Or from repo root:
#   .\ops\scripts\claude-quickstart.ps1

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
Set-Location $RepoRoot

Write-Host "== Claude quickstart (repo: $RepoRoot) ==" -ForegroundColor Cyan

$choiceFile = Join-Path $RepoRoot ".assistant-choice"
$choice = "claude"
if (Test-Path $choiceFile) {
    $existing = (Get-Content $choiceFile -Raw).Trim().ToLowerInvariant()
    if ($existing -and $existing -ne $choice -and -not $Force) {
        Write-Host "This clone is currently configured for '$existing'." -ForegroundColor Yellow
        Write-Host "To switch to Claude, re-run with -Force." -ForegroundColor Yellow
        exit 1
    }
}
Set-Content -Path $choiceFile -Value $choice -NoNewline
Write-Host "Assistant choice for this clone: $choice" -ForegroundColor Green

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "git is required on PATH." -ForegroundColor Red
    exit 1
}

git submodule update --init --recursive

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found. Install from https://docs.astral.sh/uv/ then re-run this script." -ForegroundColor Yellow
    Write-Host "Fallback: python -m pip install -e `".[dev]`"" -ForegroundColor Yellow
    exit 1
}

Write-Host "uv sync --extra dev ..." -ForegroundColor Cyan
uv sync --extra dev

Write-Host ""
Write-Host "Next (human, ~30 seconds):" -ForegroundColor Cyan
Write-Host "  1. Run: uipath-claude chat" -ForegroundColor White
Write-Host "  2. Run /status and /skills in chat" -ForegroundColor White
Write-Host "  3. If Bedrock auth fails, run: aws sts get-caller-identity" -ForegroundColor White
