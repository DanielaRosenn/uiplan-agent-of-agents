# Deploy UiPath Flows to Orchestrator
# Packages and deploys all AgentHack flows

param(
    [string]$FolderPath = "Shared",
    [string]$Environment = "Test",
    [switch]$SkipTests,
    [switch]$Force
)

Write-Host "🚀 UiPath Builder Agent - Flow Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$flows = @(
    @{
        Name = "enterprise-intake-flow"
        Path = "flows/enterprise-intake-flow"
        Description = "Enterprise intake triage and routing"
    },
    @{
        Name = "solution-planning-flow"
        Path = "flows/solution-planning-flow"
        Description = "Solution planning and approval workflow"
    },
    @{
        Name = "evidence-collection-flow"
        Path = "flows/evidence-collection-flow"
        Description = "Evidence collection and deployment gate"
    },
    @{
        Name = "agent-monitoring-flow"
        Path = "flows/agent-monitoring-flow"
        Description = "Agent health and performance monitoring"
    },
    @{
        Name = "reporting-flow"
        Path = "flows/reporting-flow"
        Description = "Automated reporting and metrics"
    }
)

# Check authentication
Write-Host "📋 Step 1: Checking Authentication..." -ForegroundColor Yellow
$loginStatus = uip login status --output json 2>&1 | ConvertFrom-Json
if ($loginStatus.loggedIn -ne $true) {
    Write-Host "❌ Not logged in. Please run: uip login" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Authenticated as: $($loginStatus.userId)" -ForegroundColor Green
Write-Host ""

# Validate flows exist
Write-Host "📋 Step 2: Validating Flow Files..." -ForegroundColor Yellow
$missingFlows = @()
foreach ($flow in $flows) {
    $flowFile = Join-Path $flow.Path "flow.json"
    if (!(Test-Path $flowFile)) {
        Write-Host "  ❌ Missing: $flowFile" -ForegroundColor Red
        $missingFlows += $flow.Name
    } else {
        Write-Host "  ✅ Found: $($flow.Name)" -ForegroundColor Green
    }
}

if ($missingFlows.Count -gt 0) {
    Write-Host ""
    Write-Host "❌ Missing flow files. Cannot proceed." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Deploy flows
Write-Host "📋 Step 3: Deploying Flows to Orchestrator..." -ForegroundColor Yellow
Write-Host ""

$deployed = 0
$failed = 0

foreach ($flow in $flows) {
    Write-Host "  Deploying: $($flow.Name)" -ForegroundColor Cyan
    Write-Host "    Path: $($flow.Path)" -ForegroundColor Gray
    Write-Host "    Description: $($flow.Description)" -ForegroundColor Gray
    
    # Note: Flow CLI deployment commands may vary based on UiPath CLI version
    # This is a placeholder for when Flow CLI support is fully available
    
    Write-Host "    📝 Manual deployment required via Studio Web:" -ForegroundColor Yellow
    Write-Host "       1. Open Studio Web: https://cloud.uipath.com/studio" -ForegroundColor Gray
    Write-Host "       2. Navigate to Flows" -ForegroundColor Gray
    Write-Host "       3. Click 'Import Flow'" -ForegroundColor Gray
    Write-Host "       4. Upload: $($flow.Path)/flow.json" -ForegroundColor Gray
    Write-Host "       5. Configure connections" -ForegroundColor Gray
    Write-Host "       6. Publish to folder: $FolderPath" -ForegroundColor Gray
    Write-Host ""
    
    # When CLI support is available, use:
    # uip flow pack $flow.Path
    # uip flow deploy --package "$($flow.Name).1.0.0.nupkg" --folder-path $FolderPath
}

Write-Host ""

# Summary
Write-Host "📋 Step 4: Deployment Summary" -ForegroundColor Yellow
Write-Host ""
Write-Host "Target Environment: $Environment" -ForegroundColor White
Write-Host "Target Folder: $FolderPath" -ForegroundColor White
Write-Host "Flows: $($flows.Count)" -ForegroundColor White
Write-Host ""

Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Deploy flows via Studio Web (see instructions above)" -ForegroundColor White
Write-Host "  2. Configure Integration Service connections" -ForegroundColor White
Write-Host "     - Outlook connector for email notifications" -ForegroundColor Gray
Write-Host "  3. Verify queue names match Orchestrator queues" -ForegroundColor White
Write-Host "  4. Test each flow with sample inputs" -ForegroundColor White
Write-Host "  5. Run: .\verify-flows.ps1 to validate deployment" -ForegroundColor White
Write-Host ""

Write-Host "✅ Flow deployment preparation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "For automated deployment when CLI supports it, this script will be updated." -ForegroundColor Yellow
