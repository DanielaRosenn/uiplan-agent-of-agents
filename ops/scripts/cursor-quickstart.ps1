# One-shot Cursor + MCP setup after clone (minimal manual steps).
# Requires: git, uv (https://docs.astral.sh/uv/). Run from anywhere.
#
#   pwsh -File ops/scripts/cursor-quickstart.ps1
# Or from repo root:
#   .\ops\scripts\cursor-quickstart.ps1

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
Set-Location $RepoRoot

Write-Host "== Cursor quickstart (repo: $RepoRoot) ==" -ForegroundColor Cyan

$choiceFile = Join-Path $RepoRoot ".assistant-choice"
$choice = "cursor"
if (Test-Path $choiceFile) {
    $existing = (Get-Content $choiceFile -Raw).Trim().ToLowerInvariant()
    if ($existing -and $existing -ne $choice -and -not $Force) {
        Write-Host "This clone is currently configured for '$existing'." -ForegroundColor Yellow
        Write-Host "To switch to Cursor, re-run with -Force." -ForegroundColor Yellow
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
    Write-Host "Fallback: python -m pip install -e `".[mcp]`" (then copy .cursor/mcp.json.example manually)." -ForegroundColor Yellow
    exit 1
}

Write-Host "uv sync --extra mcp ..." -ForegroundColor Cyan
uv sync --extra mcp

$cursorDir = Join-Path $RepoRoot ".cursor"
$mcpExample = Join-Path $RepoRoot ".cursor\mcp.json.example"
$mcpLocal = Join-Path $RepoRoot ".cursor\mcp.json"
if (-not (Test-Path $cursorDir)) {
    New-Item -ItemType Directory -Path $cursorDir | Out-Null
}
if (-not (Test-Path $mcpLocal)) {
    if (-not (Test-Path $mcpExample)) {
        Write-Host "Missing .cursor/mcp.json.example — checkout may be incomplete." -ForegroundColor Red
        exit 1
    }
    Copy-Item $mcpExample $mcpLocal
    Write-Host "Created .cursor/mcp.json from mcp.json.example" -ForegroundColor Green
} else {
    Write-Host ".cursor/mcp.json already exists (left unchanged)." -ForegroundColor DarkYellow
}

if ($Force) {
    & (Join-Path $ScriptDir "setup-cursor.ps1") -Force
} else {
    & (Join-Path $ScriptDir "setup-cursor.ps1")
}

Write-Host ""
Write-Host "Next (human, ~30 seconds):" -ForegroundColor Cyan
Write-Host "  1. File -> Open Folder -> select this repo root" -ForegroundColor White
Write-Host "  2. Cursor: Settings -> MCP -> confirm uipath-builder-agent is green" -ForegroundColor White
Write-Host "  3. Command Palette -> Developer: Reload Window (if MCP was red)" -ForegroundColor White
Write-Host ""
Write-Host "Optional: add cursor-public/superpowers to cursor.plugins (see CURSOR_USER_GUIDE.md)." -ForegroundColor DarkGray
