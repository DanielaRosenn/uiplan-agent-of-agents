# Regenerates XAML and runs Workflow Analyzer. ST-USG-034 (Automation Hub URL) is
# tenant-specific; ignore it here and assert no other analyzer errors (ErrorSeverity 1).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$proj = Join-Path $root "InvoiceIntake_Demo\project.json"
$result = Join-Path $root "InvoiceIntake_Demo\analyze.json"

if (-not (Test-Path $proj)) { throw "Missing $proj" }

python (Join-Path $PSScriptRoot "emit_invoice_intake_xaml.py")
uipcli package analyze $proj `
    --ignoredRules ST-USG-034 `
    --resultPath $result

$items = Get-Content $result -Raw | ConvertFrom-Json
$errors = @($items | Where-Object { $_.ErrorSeverity -eq 1 })
if ($errors.Count -gt 0) {
    $errors | ConvertTo-Json -Depth 6
    throw "Analyzer reported $($errors.Count) error(s). See JSON above."
}
Write-Host "OK: No analyzer errors (ST-USG-034 ignored). Items in report: $($items.Count)."
