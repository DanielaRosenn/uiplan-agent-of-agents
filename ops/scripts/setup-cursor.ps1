# Setup Cursor skills for UiPath Builder Agent
# Run this script after cloning to enable Cursor skill discovery

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
# Script lives at <repo>/ops/scripts/ — repo root is two levels up
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$CursorSkillsDir = Join-Path $RepoRoot ".cursor\skills"
$SourceSkillsDir = Join-Path $RepoRoot "skills\skills"
$OverlaySkillsDir = Join-Path $RepoRoot "extensions\skills"

Write-Host "Setting up Cursor skills..." -ForegroundColor Cyan

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

# Check if source skills exist
if (-not (Test-Path $SourceSkillsDir)) {
    Write-Host "Error: skills/skills directory not found." -ForegroundColor Red
    Write-Host "Run: git submodule update --init --recursive" -ForegroundColor Yellow
    exit 1
}

# Create .cursor directory if needed
$CursorDir = Join-Path $RepoRoot ".cursor"
if (-not (Test-Path $CursorDir)) {
    New-Item -ItemType Directory -Path $CursorDir | Out-Null
}

# Check if skills directory already exists
if (Test-Path $CursorSkillsDir) {
    if ($Force) {
        Write-Host "Removing existing .cursor/skills..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $CursorSkillsDir
    } else {
        Write-Host ".cursor/skills already exists. Use -Force to recreate." -ForegroundColor Yellow
        exit 0
    }
}

# Build a generated physical view. This preserves local Cursor overlays
# (uiplan, mermaid guidance, legacy redirects) while keeping skills/skills
# as the official upstream source of truth.
New-Item -ItemType Directory -Path $CursorSkillsDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $SourceSkillsDir "*") $CursorSkillsDir
if (Test-Path $OverlaySkillsDir) {
    Get-ChildItem -Path $OverlaySkillsDir -Directory | ForEach-Object {
        Copy-Item -Recurse -Force $_.FullName $CursorSkillsDir
    }
}
Write-Host "Generated .cursor/skills from skills/skills plus extensions/skills overlays" -ForegroundColor Green
Write-Host "Re-run this script after pulling changes or advancing the skills submodule." -ForegroundColor Yellow

Write-Host ""
Write-Host "Cursor setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Available UiPath skills:" -ForegroundColor Cyan
Get-ChildItem -Path $CursorSkillsDir -Directory | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor White
}
Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "STEP 2: Install MCP Tools (Optional)" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Python deps (if not already done):" -ForegroundColor Cyan
Write-Host "  uv sync --extra mcp   OR   pip install -e `".[mcp]`"" -ForegroundColor White
Write-Host "  Or run: ops/scripts/cursor-quickstart.ps1 (does uv + MCP copy + this script)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "MCP config is at: .cursor/mcp.json" -ForegroundColor Cyan
Write-Host "Cursor will auto-detect it when you open the folder." -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "STEP 3: Install Superpowers Plugin" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Add to Cursor settings.json:" -ForegroundColor Cyan
Write-Host '  "cursor.plugins": ["cursor-public/superpowers"]' -ForegroundColor White
Write-Host ""
Write-Host "Superpowers adds:" -ForegroundColor Cyan
Write-Host "  - brainstorming      (design before code)" -ForegroundColor White
Write-Host "  - writing-plans      (implementation plans)" -ForegroundColor White
Write-Host "  - executing-plans    (task-by-task execution)" -ForegroundColor White
Write-Host "  - test-driven-dev    (TDD workflow)" -ForegroundColor White
Write-Host "  - systematic-debug   (bug investigation)" -ForegroundColor White
Write-Host "  - code-review        (quality checks)" -ForegroundColor White
Write-Host ""
Write-Host "See docs/CURSOR_USER_GUIDE.md for full documentation." -ForegroundColor Cyan
Write-Host ""
Write-Host "Open this folder in Cursor to start building UiPath workflows." -ForegroundColor Green
