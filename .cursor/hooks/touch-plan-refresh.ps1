$ErrorActionPreference = "Stop"

function Emit-Empty {
    '{}' | Write-Output
    exit 0
}

function Get-StringValues($value) {
    if ($null -eq $value) {
        return
    }
    if ($value -is [string]) {
        $value
        return
    }
    if ($value -is [System.Collections.IDictionary]) {
        foreach ($item in $value.Values) {
            Get-StringValues $item
        }
        return
    }
    if ($value.PSObject -and $value.PSObject.Properties.Count -gt 0) {
        foreach ($property in $value.PSObject.Properties) {
            Get-StringValues $property.Value
        }
        return
    }
    if ($value -is [System.Collections.IEnumerable]) {
        foreach ($item in $value) {
            Get-StringValues $item
        }
    }
}

function Test-PlanPath([string] $rawPath) {
    $normalized = $rawPath.Replace('\', '/')
    if ($normalized -notmatch '(^|/)(\.cursor/plans|docs/plans)/') {
        return $false
    }
    return $normalized -match '/(spec|plan|tasks)\.md$' -or $normalized -match '\.md$'
}

try {
    $inputJson = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($inputJson)) {
        Emit-Empty
    }

    $payload = $inputJson | ConvertFrom-Json -ErrorAction Stop
    $changedPaths = @(Get-StringValues $payload | Where-Object { Test-PlanPath $_ } | Select-Object -Unique)
    if ($changedPaths.Count -eq 0) {
        Emit-Empty
    }

    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    $stateDir = Join-Path $repoRoot ".uiplan"
    if (-not (Test-Path $stateDir)) {
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    }

    $marker = Join-Path $stateDir "studio-refresh.json"
    $state = @{
        updated_at = (Get-Date).ToUniversalTime().ToString("o")
        paths = $changedPaths
        source = "cursor-afterFileEdit"
    }
    $state | ConvertTo-Json -Depth 4 | Set-Content -Path $marker -Encoding UTF8
    '{}' | Write-Output
    exit 0
} catch {
    Emit-Empty
}
