# Orchestrator Setup Script for AgentHack Flows
# Creates queues, storage buckets, and prepares environment for flow deployment

param(
    [string]$OrganizationUrl = "https://cloud.uipath.com/your-org",
    [string]$TenantName = "Test",
    [string]$FolderPath = "Shared",
    [string]$ClientId,
    [string]$ClientSecret
)

Write-Host "🚀 UiPath Builder Agent - Orchestrator Setup" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Authenticate
Write-Host "📋 Step 1: Authenticating with Orchestrator..." -ForegroundColor Yellow
if ($ClientId -and $ClientSecret) {
    Write-Host "Using client credentials..."
    # TODO: Add OAuth2 authentication when available
    Write-Host "⚠️  Client credential auth not yet implemented in this script" -ForegroundColor Yellow
    Write-Host "Please authenticate manually: uip login" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "Checking authentication status..."
    $loginStatus = uip login status --output json 2>&1 | ConvertFrom-Json
    if ($loginStatus.loggedIn -ne $true) {
        Write-Host "❌ Not logged in. Please run: uip login" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Already authenticated" -ForegroundColor Green
}

Write-Host ""

# Create Queues
Write-Host "📋 Step 2: Creating Orchestrator Queues..." -ForegroundColor Yellow

$queues = @(
    @{Name="Q_FINANCE_INTAKE"; Description="Finance department automation intake requests"},
    @{Name="Q_HR_INTAKE"; Description="HR department automation intake requests"},
    @{Name="Q_OPS_INTAKE"; Description="Operations department automation intake requests"},
    @{Name="Q_SHARED_INTAKE"; Description="Shared/general automation intake requests"},
    @{Name="Q_PLANNING_REQUESTS"; Description="Solution planning and review requests"},
    @{Name="Q_IMPLEMENTATION_READY"; Description="Approved plans ready for implementation"},
    @{Name="Q_DEPLOYMENT_READY"; Description="Projects ready for deployment validation"}
)

foreach ($queue in $queues) {
    Write-Host "  Creating queue: $($queue.Name)..." -ForegroundColor Gray
    
    # Check if queue exists
    $existingQueue = uip orchestrator queues list --folder-path $FolderPath --output json 2>&1 | ConvertFrom-Json | Where-Object { $_.Name -eq $queue.Name }
    
    if ($existingQueue) {
        Write-Host "    ⚠️  Queue already exists: $($queue.Name)" -ForegroundColor Yellow
    } else {
        # Create queue
        try {
            uip orchestrator queues create `
                --name $queue.Name `
                --description $queue.Description `
                --folder-path $FolderPath `
                --max-number-of-retries 3 `
                --accept-automatically-retry false
            Write-Host "    ✅ Created: $($queue.Name)" -ForegroundColor Green
        } catch {
            Write-Host "    ❌ Failed to create: $($queue.Name)" -ForegroundColor Red
            Write-Host "       Error: $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Create Storage Buckets
Write-Host "📋 Step 3: Creating Storage Buckets..." -ForegroundColor Yellow

$buckets = @(
    @{Name="planning-artifacts"; Description="Solution planning artifacts (spec, plan, tasks)"},
    @{Name="test-results"; Description="Test execution results and evidence"},
    @{Name="evidence-packages"; Description="Deployment evidence packages"},
    @{Name="monitoring-data"; Description="Orchestrator and agent monitoring data"}
)

foreach ($bucket in $buckets) {
    Write-Host "  Creating storage bucket: $($bucket.Name)..." -ForegroundColor Gray
    
    # Note: Storage bucket creation via CLI may not be available yet
    Write-Host "    ⚠️  Storage bucket creation via CLI not yet available" -ForegroundColor Yellow
    Write-Host "    📝 Manual step: Create bucket '$($bucket.Name)' in Orchestrator UI" -ForegroundColor Cyan
    Write-Host "       Description: $($bucket.Description)" -ForegroundColor Gray
}

Write-Host ""

# Create Assets
Write-Host "📋 Step 4: Creating Orchestrator Assets..." -ForegroundColor Yellow

$assets = @(
    @{Name="CI_API_TOKEN"; Type="text"; Description="API token for CI/CD telemetry collection"},
    @{Name="SMTP_SERVER"; Type="text"; Description="SMTP server for email notifications"},
    @{Name="ALERT_EMAIL_LIST"; Type="text"; Description="Comma-separated list of alert recipients"},
    @{Name="ASSET_FINANCE_POLICY"; Type="text"; Description="Finance department policy URL"},
    @{Name="ASSET_HR_POLICY"; Type="text"; Description="HR department policy URL"},
    @{Name="ASSET_SHARED_POLICY"; Type="text"; Description="Shared/default policy URL"}
)

foreach ($asset in $assets) {
    Write-Host "  Creating asset: $($asset.Name)..." -ForegroundColor Gray
    
    # Check if asset exists
    $existingAsset = uip orchestrator assets list --folder-path $FolderPath --output json 2>&1 | ConvertFrom-Json | Where-Object { $_.Name -eq $asset.Name }
    
    if ($existingAsset) {
        Write-Host "    ⚠️  Asset already exists: $($asset.Name)" -ForegroundColor Yellow
    } else {
        Write-Host "    📝 Manual step: Create asset '$($asset.Name)' in Orchestrator UI" -ForegroundColor Cyan
        Write-Host "       Type: $($asset.Type)" -ForegroundColor Gray
        Write-Host "       Description: $($asset.Description)" -ForegroundColor Gray
    }
}

Write-Host ""

# Summary
Write-Host "📋 Step 5: Setup Summary" -ForegroundColor Yellow
Write-Host ""
Write-Host "✅ Orchestrator Authentication: OK" -ForegroundColor Green
Write-Host "✅ Queue Creation: $($queues.Count) queues configured" -ForegroundColor Green
Write-Host "⚠️  Storage Buckets: $($buckets.Count) buckets require manual creation" -ForegroundColor Yellow
Write-Host "⚠️  Assets: $($assets.Count) assets require manual creation" -ForegroundColor Yellow
Write-Host ""

Write-Host "📝 Manual Steps Required:" -ForegroundColor Cyan
Write-Host "  1. Create storage buckets in Orchestrator UI:" -ForegroundColor White
foreach ($bucket in $buckets) {
    Write-Host "     - $($bucket.Name)" -ForegroundColor Gray
}
Write-Host ""
Write-Host "  2. Create assets in Orchestrator UI:" -ForegroundColor White
foreach ($asset in $assets) {
    Write-Host "     - $($asset.Name) ($($asset.Type))" -ForegroundColor Gray
}
Write-Host ""

Write-Host "✅ Orchestrator setup complete!" -ForegroundColor Green
Write-Host "Next: Deploy flows using deploy-flows.ps1" -ForegroundColor Cyan
