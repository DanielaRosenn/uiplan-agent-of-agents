# Record the hero terminal cast for the README.
# Requires: vhs (https://github.com/charmbracelet/vhs) on PATH.
#
# Usage:
#   .\ops\scripts\record-demo.ps1
#
# Output:
#   docs/assets/demo.gif
#
# Prerequisites on the recording machine:
#   - UiPath Claude Code installed (pip install -e ".[dev]")
#   - AWS Bedrock creds valid (aws sts get-caller-identity)
#   - UiPath Studio Desktop 26.2+ running
#   - $env:UIPATH_AGENTIC_MODE = "1"

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tape = Join-Path $repoRoot "docs\assets\demo.tape"

if (-not (Get-Command vhs -ErrorAction SilentlyContinue)) {
    Write-Error "vhs not found on PATH. Install from https://github.com/charmbracelet/vhs and retry."
}

if (-not (Test-Path $tape)) {
    Write-Error "Tape file not found: $tape"
}

Push-Location $repoRoot
try {
    Write-Host "Recording $tape ..." -ForegroundColor Cyan
    vhs $tape
    Write-Host "Rendered docs/assets/demo.gif" -ForegroundColor Green
}
finally {
    Pop-Location
}
