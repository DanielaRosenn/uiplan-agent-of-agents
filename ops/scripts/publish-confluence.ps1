# Publish docs/wiki/confluence-*.md to the Cato RPA Confluence space.
#
# Loads environment variables from .env at the repo root (if present) and
# invokes ops/scripts/publish_confluence.py.
#
# Usage:
#   .\ops\scripts\publish-confluence.ps1            # real publish
#   .\ops\scripts\publish-confluence.ps1 -DryRun    # no API calls, prints payloads

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot ".env"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $kv = $line -split "=", 2
        if ($kv.Count -eq 2) {
            $name = $kv[0].Trim()
            $value = $kv[1].Trim().Trim('"').Trim("'")
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

$python = if ($env:VIRTUAL_ENV) {
    Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
} else {
    "python"
}

# On Cato laptops, the corporate proxy performs TLS inspection with a private
# root CA. The venv's bundled certifi bundle does not trust it, but the
# user-scope certifi bundle under %LOCALAPPDATA%\.certifi does (pip installs
# it). Point SSL_CERT_FILE there so httpx can validate cloud.uipath.com.
if (-not $env:SSL_CERT_FILE) {
    $userCert = Join-Path $env:LOCALAPPDATA ".certifi\cacert.pem"
    if (Test-Path $userCert) {
        $env:SSL_CERT_FILE = $userCert
    }
}

$script = Join-Path $repoRoot "scripts\publish_confluence.py"
$publishArgs = @()
if ($DryRun) { $publishArgs += "--dry-run" }

Push-Location $repoRoot
try {
    & $python $script @publishArgs
    if ($LASTEXITCODE -ne 0) {
        throw "publish_confluence.py exited with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
