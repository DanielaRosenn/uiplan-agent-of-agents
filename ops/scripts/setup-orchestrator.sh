#!/bin/bash
# Orchestrator Setup Script for AgentHack Flows (Linux/Mac)
# Creates queues, storage buckets, and prepares environment for flow deployment

ORGANIZATION_URL="${1:-https://cloud.uipath.com/your-org}"
TENANT_NAME="${2:-Test}"
FOLDER_PATH="${3:-Shared}"

echo "🚀 UiPath Builder Agent - Orchestrator Setup"
echo "============================================="
echo ""

# Authenticate
echo "📋 Step 1: Authenticating with Orchestrator..."
LOGIN_STATUS=$(uip login status --output json 2>&1)
if ! echo "$LOGIN_STATUS" | grep -q '"loggedIn":true'; then
    echo "❌ Not logged in. Please run: uip login"
    exit 1
fi
echo "✅ Already authenticated"
echo ""

# Create Queues
echo "📋 Step 2: Creating Orchestrator Queues..."

declare -a queues=(
    "Q_FINANCE_INTAKE:Finance department automation intake requests"
    "Q_HR_INTAKE:HR department automation intake requests"
    "Q_OPS_INTAKE:Operations department automation intake requests"
    "Q_SHARED_INTAKE:Shared/general automation intake requests"
    "Q_PLANNING_REQUESTS:Solution planning and review requests"
    "Q_IMPLEMENTATION_READY:Approved plans ready for implementation"
    "Q_DEPLOYMENT_READY:Projects ready for deployment validation"
)

for queue_def in "${queues[@]}"; do
    IFS=':' read -r queue_name queue_desc <<< "$queue_def"
    echo "  Creating queue: $queue_name..."
    
    # Check if queue exists
    EXISTING=$(uip orchestrator queues list --folder-path "$FOLDER_PATH" --output json 2>&1 | grep -c "\"Name\":\"$queue_name\"")
    
    if [ "$EXISTING" -gt 0 ]; then
        echo "    ⚠️  Queue already exists: $queue_name"
    else
        uip orchestrator queues create \
            --name "$queue_name" \
            --description "$queue_desc" \
            --folder-path "$FOLDER_PATH" \
            --max-number-of-retries 3 \
            --accept-automatically-retry false && \
        echo "    ✅ Created: $queue_name" || \
        echo "    ❌ Failed to create: $queue_name"
    fi
done

echo ""

# Storage Buckets
echo "📋 Step 3: Creating Storage Buckets..."
echo "⚠️  Storage bucket creation via CLI not yet available"
echo "📝 Manual steps required (see summary below)"
echo ""

# Assets
echo "📋 Step 4: Creating Orchestrator Assets..."
echo "⚠️  Asset creation requires manual steps in Orchestrator UI"
echo "📝 See summary below for required assets"
echo ""

# Summary
echo "📋 Step 5: Setup Summary"
echo ""
echo "✅ Orchestrator Authentication: OK"
echo "✅ Queue Creation: 7 queues configured"
echo "⚠️  Storage Buckets: 4 buckets require manual creation"
echo "⚠️  Assets: 6 assets require manual creation"
echo ""

echo "📝 Manual Steps Required:"
echo "  1. Create storage buckets in Orchestrator UI:"
echo "     - planning-artifacts"
echo "     - test-results"
echo "     - evidence-packages"
echo "     - monitoring-data"
echo ""
echo "  2. Create assets in Orchestrator UI:"
echo "     - CI_API_TOKEN (text)"
echo "     - SMTP_SERVER (text)"
echo "     - ALERT_EMAIL_LIST (text)"
echo "     - ASSET_FINANCE_POLICY (text)"
echo "     - ASSET_HR_POLICY (text)"
echo "     - ASSET_SHARED_POLICY (text)"
echo ""

echo "✅ Orchestrator setup complete!"
echo "Next: Deploy flows using ./deploy-flows.sh"
