# Verify Flow Deployment
# Tests deployed flows and validates configuration

param(
    [string]$FolderPath = "Shared",
    [switch]$Verbose
)

Write-Host "🔍 UiPath Builder Agent - Flow Deployment Verification" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# Check authentication
Write-Host "📋 Step 1: Verifying Authentication..." -ForegroundColor Yellow
$loginStatus = uip login status --output json 2>&1 | ConvertFrom-Json
if ($loginStatus.loggedIn -ne $true) {
    Write-Host "❌ Not logged in" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Authenticated" -ForegroundColor Green
Write-Host ""

# Check queues
Write-Host "📋 Step 2: Verifying Orchestrator Queues..." -ForegroundColor Yellow

$requiredQueues = @(
    "Q_FINANCE_INTAKE",
    "Q_HR_INTAKE",
    "Q_OPS_INTAKE",
    "Q_SHARED_INTAKE",
    "Q_PLANNING_REQUESTS",
    "Q_IMPLEMENTATION_READY",
    "Q_DEPLOYMENT_READY"
)

$existingQueues = uip orchestrator queues list --folder-path $FolderPath --output json 2>&1 | ConvertFrom-Json

$missingQueues = @()
foreach ($queueName in $requiredQueues) {
    $found = $existingQueues | Where-Object { $_.Name -eq $queueName }
    if ($found) {
        Write-Host "  ✅ Queue exists: $queueName" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Queue missing: $queueName" -ForegroundColor Red
        $missingQueues += $queueName
    }
}

if ($missingQueues.Count -gt 0) {
    Write-Host ""
    Write-Host "⚠️  Missing queues detected. Run setup-orchestrator.ps1 first." -ForegroundColor Yellow
}
Write-Host ""

# Check assets
Write-Host "📋 Step 3: Verifying Orchestrator Assets..." -ForegroundColor Yellow

$requiredAssets = @(
    "CI_API_TOKEN",
    "ALERT_EMAIL_LIST",
    "ASSET_FINANCE_POLICY",
    "ASSET_HR_POLICY",
    "ASSET_SHARED_POLICY"
)

$existingAssets = uip orchestrator assets list --folder-path $FolderPath --output json 2>&1 | ConvertFrom-Json

$missingAssets = @()
foreach ($assetName in $requiredAssets) {
    $found = $existingAssets | Where-Object { $_.Name -eq $assetName }
    if ($found) {
        Write-Host "  ✅ Asset exists: $assetName" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Asset missing: $assetName" -ForegroundColor Red
        $missingAssets += $assetName
    }
}

if ($missingAssets.Count -gt 0) {
    Write-Host ""
    Write-Host "⚠️  Missing assets detected. Create manually in Orchestrator UI." -ForegroundColor Yellow
}
Write-Host ""

# Check flows (via Studio Web)
Write-Host "📋 Step 4: Checking Flow Deployment Status..." -ForegroundColor Yellow
Write-Host "⚠️  Flow verification requires manual check in Studio Web" -ForegroundColor Yellow
Write-Host ""
Write-Host "Manual verification steps:" -ForegroundColor Cyan
Write-Host "  1. Open Studio Web: https://cloud.uipath.com/studio" -ForegroundColor Gray
Write-Host "  2. Navigate to Flows" -ForegroundColor Gray
Write-Host "  3. Verify these flows are published:" -ForegroundColor Gray
Write-Host "     - enterprise-intake-flow" -ForegroundColor Gray
Write-Host "     - solution-planning-flow" -ForegroundColor Gray
Write-Host "     - evidence-collection-flow" -ForegroundColor Gray
Write-Host "     - agent-monitoring-flow" -ForegroundColor Gray
Write-Host "     - reporting-flow" -ForegroundColor Gray
Write-Host ""

# Summary
Write-Host "📋 Step 5: Verification Summary" -ForegroundColor Yellow
Write-Host ""

$allGood = ($missingQueues.Count -eq 0) -and ($missingAssets.Count -eq 0)

if ($allGood) {
    Write-Host "✅ All Orchestrator prerequisites verified!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Manually verify flows are deployed in Studio Web" -ForegroundColor White
    Write-Host "  2. Configure Integration Service connections" -ForegroundColor White
    Write-Host "  3. Test flows with sample inputs" -ForegroundColor White
} else {
    Write-Host "⚠️  Some prerequisites are missing:" -ForegroundColor Yellow
    Write-Host ""
    if ($missingQueues.Count -gt 0) {
        Write-Host "Missing Queues:" -ForegroundColor Red
        foreach ($queue in $missingQueues) {
            Write-Host "  - $queue" -ForegroundColor Gray
        }
    }
    if ($missingAssets.Count -gt 0) {
        Write-Host "Missing Assets:" -ForegroundColor Red
        foreach ($asset in $missingAssets) {
            Write-Host "  - $asset" -ForegroundColor Gray
        }
    }
    Write-Host ""
    Write-Host "Run setup-orchestrator.ps1 to create missing items." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Verification complete!" -ForegroundColor Green
