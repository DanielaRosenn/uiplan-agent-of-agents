# UiPath Flow Deployment Guide

Complete guide for deploying AgentHack flows to Orchestrator.

---

## Quick Start

### 1. Setup Orchestrator Prerequisites

**Windows:**
```powershell
.\ops\scripts\setup-orchestrator.ps1
```

**Linux/Mac:**
```bash
bash ops/scripts/setup-orchestrator.sh
```

This creates:
- 7 Orchestrator queues
- Instructions for 4 storage buckets
- Instructions for 6 assets

### 2. Deploy Flows

**Prepare deployment:**
```powershell
.\ops\scripts\deploy-flows.ps1
```

**Deploy via Studio Web:**
1. Open https://cloud.uipath.com/studio
2. Navigate to **Flows**
3. Click **Import Flow**
4. Upload each `flow.json` from `flows/*/flow.json`
5. Configure Integration Service connections
6. Click **Publish** to Orchestrator

### 3. Verify Deployment

```powershell
.\ops\scripts\verify-flows.ps1
```

---

## Available Flows

### 1. Enterprise Intake Triage Flow
**File:** `flows/enterprise-intake-flow/flow.json`

**Purpose:** Routes business intake requests to appropriate handlers

**Trigger:** Manual

**Inputs:**
- `businessUnit`: FINANCE, HR, OPS, etc.
- `intakeId`: Unique identifier
- `requestSummary`: Brief description
- `stakeholders`: Email addresses

**What it does:**
1. Receives intake request
2. Classifies by business unit
3. Routes to appropriate queue
4. Sends email notification
5. Invokes builder orchestrator agent

---

### 2. Solution Planning & Review Flow
**File:** `flows/solution-planning-flow/flow.json`

**Purpose:** Orchestrates planning artifact generation and approval

**Trigger:** Queue (`Q_PLANNING_REQUESTS`)

**What it does:**
1. Extract intake data from queue
2. Invoke discovery agent
3. Invoke solution architect agent
4. Store artifacts (spec/plan/tasks)
5. Create Action Center approval task
6. Evaluate approval decision
7. Invoke verifier agent (if approved)
8. Send notifications

---

### 3. Evidence Collection & Deployment Gate Flow
**File:** `flows/evidence-collection-flow/flow.json`

**Purpose:** Collects validation evidence and controls deployment

**Trigger:** Manual

**Inputs:**
- `intakeId`: Project identifier
- `projectPath`: Path to artifacts
- `environment`: dev, test, or prod

**What it does:**
1. Collect CI/CD telemetry
2. Collect test results
3. Invoke deployment evidence agent
4. Evaluate readiness
5. Check environment (prod requires approval)
6. Deploy and run smoke test
7. Send notifications

---

### 4. Agent Monitoring Flow
**File:** `flows/agent-monitoring-flow/flow.json`

**Purpose:** Monitors agent health and performance

**Trigger:** Schedule (every 5 minutes)

**What it does:**
1. Collect agent execution metrics
2. Analyze health scores
3. Check alert thresholds
4. Send alerts if needed
5. Store metrics
6. Update dashboard

---

### 5. Reporting Flow
**File:** `flows/reporting-flow/flow.json`

**Purpose:** Generates daily reports and metrics

**Trigger:** Schedule (daily at 8 AM)

**What it does:**
1. Define report period
2. Collect intake metrics
3. Collect agent metrics
4. Collect deployment metrics
5. Aggregate all data
6. Generate markdown report
7. Store report
8. Distribute via email
9. Send alerts if performance is poor

---

## Prerequisites

### Orchestrator Queues

Create these queues in Orchestrator (folder: Shared):

| Queue Name | Description |
|------------|-------------|
| `Q_FINANCE_INTAKE` | Finance department intake |
| `Q_HR_INTAKE` | HR department intake |
| `Q_OPS_INTAKE` | Operations department intake |
| `Q_SHARED_INTAKE` | Shared/general intake |
| `Q_PLANNING_REQUESTS` | Planning requests |
| `Q_IMPLEMENTATION_READY` | Ready for implementation |
| `Q_DEPLOYMENT_READY` | Ready for deployment |

### Storage Buckets

Create these storage buckets in Orchestrator:

| Bucket Name | Description |
|-------------|-------------|
| `planning-artifacts` | Spec, plan, tasks files |
| `test-results` | Test execution results |
| `evidence-packages` | Deployment evidence |
| `monitoring-data` | Agent health metrics |

### Orchestrator Assets

Create these assets in Orchestrator (folder: Shared):

| Asset Name | Type | Description |
|------------|------|-------------|
| `CI_API_TOKEN` | Text | CI/CD telemetry API token |
| `SMTP_SERVER` | Text | Email server (optional) |
| `ALERT_EMAIL_LIST` | Text | Comma-separated alert emails |
| `ASSET_FINANCE_POLICY` | Text | Finance policy URL |
| `ASSET_HR_POLICY` | Text | HR policy URL |
| `ASSET_SHARED_POLICY` | Text | Shared policy URL |

### Integration Service Connections

Configure in Integration Service:

1. **Outlook Connector**
   - Purpose: Send email notifications
   - Required permissions: Send email
   - Test connection before deploying flows

---

## Deployment Steps

### Step 1: Authenticate

```powershell
uip login
```

Follow the browser authentication flow.

### Step 2: Run Setup Script

```powershell
.\ops\scripts\setup-orchestrator.ps1
```

This creates queues automatically. Storage buckets and assets require manual creation (see prerequisites above).

### Step 3: Create Manual Resources

**Storage Buckets:**
1. Go to Orchestrator → Admin → Storage Buckets
2. Create each bucket listed in prerequisites

**Assets:**
1. Go to Orchestrator → Tenant → Assets
2. Create each asset listed in prerequisites
3. Set appropriate values

**Integration Service:**
1. Go to Integration Service
2. Add Outlook connector
3. Create connection with your email account

### Step 4: Import Flows to Studio Web

For each flow:

1. Open Studio Web: https://cloud.uipath.com/studio
2. Click **Flows** in left sidebar
3. Click **Import Flow** button
4. Upload the `flow.json` file:
   - `flows/enterprise-intake-flow/flow.json`
   - `flows/solution-planning-flow/flow.json`
   - `flows/evidence-collection-flow/flow.json`
   - `flows/agent-monitoring-flow/flow.json`
   - `flows/reporting-flow/flow.json`
5. Review flow in visual editor
6. Configure Integration Service connections
7. Click **Publish**
8. Select folder: **Shared**
9. Confirm publication

### Step 5: Verify Deployment

```powershell
.\ops\scripts\verify-flows.ps1
```

This checks:
- Orchestrator authentication
- Queue existence
- Asset existence
- Provides manual verification steps for flows

### Step 6: Test Flows

**Test Enterprise Intake Flow:**
1. Go to Orchestrator → Automations → Flows
2. Find `enterprise-intake-flow`
3. Click **Run**
4. Provide test inputs:
   ```json
   {
     "businessUnit": "FINANCE",
     "intakeId": "TEST-001",
     "requestSummary": "Test automation request",
     "stakeholders": ["your-email@company.com"]
   }
   ```
5. Verify email notification received
6. Check queue `Q_FINANCE_INTAKE` has new item

**Test Solution Planning Flow:**
1. Add test item to `Q_PLANNING_REQUESTS` queue
2. Flow should trigger automatically
3. Check Action Center for approval task
4. Approve the task
5. Verify artifacts in `planning-artifacts` bucket

**Test Evidence Collection Flow:**
1. Run manually with test data
2. Verify email notifications
3. Check deployment decision logic

---

## Troubleshooting

### Issue: Queue creation fails

**Solution:**
```powershell
# Check authentication
uip login status

# Re-authenticate if needed
uip login

# Try creating queue manually
uip orchestrator queues create --name Q_TEST --folder-path Shared
```

### Issue: Flow import fails in Studio Web

**Solution:**
- Verify `flow.json` is valid JSON
- Check that all node types are supported
- Review error message in Studio Web
- Simplify flow if needed (remove complex nodes)

### Issue: Integration Service connection not found

**Solution:**
1. Go to Integration Service
2. Verify Outlook connector is added
3. Create connection with authentication
4. In Studio Web, refresh connections
5. Re-configure flow to use correct connection

### Issue: Agent invocation fails

**Solution:**
- Verify agents are deployed to Orchestrator
- Check agent folder matches flow configuration
- Verify agent input schema matches flow
- Test agent independently first

### Issue: Storage bucket not found

**Solution:**
1. Go to Orchestrator → Admin → Storage Buckets
2. Create missing bucket
3. Verify folder access permissions
4. Re-test flow

---

## Flow Architecture

### Integration Points

```
Flows → Orchestrator Queues
      → Integration Service (Email)
      → Coded Agents
      → Action Center (Approvals)
      → Storage Buckets
      → HTTP APIs (Telemetry)
```

### Decision Logic Flow

```
Intake → Classification → Routing → Queue
      → Agent Invocation → Artifacts → Approval
      → Verification → Deployment Gate → Deploy
      → Smoke Test → Notifications
```

---

## Monitoring

### Flow Execution

Monitor flows in Orchestrator:
1. Go to **Monitoring** → **Flows**
2. View execution history
3. Check for failures
4. Review logs

### Queue Status

Check queue depth:
1. Go to **Queues**
2. View items by queue
3. Monitor processing rate
4. Identify bottlenecks

### Agent Health

Use the **Agent Monitoring Flow**:
- Runs every 5 minutes
- Alerts on degraded agents
- Stores metrics
- Updates dashboard

### Reports

Daily reports generated by **Reporting Flow**:
- Sent to configured email addresses
- Stored in `monitoring-data` bucket
- Available in markdown and JSON formats

---

## Next Steps

### For Development
1. Test flows with real data
2. Tune alert thresholds
3. Add custom metrics
4. Enhance reporting

### For Production
1. Create production queues
2. Set up change management
3. Configure approval groups
4. Establish SLAs

### For Enhancement
1. Add Slack/Teams notifications
2. Integrate with ITSM tools
3. Add custom dashboards
4. Implement advanced analytics

---

## Support

### Documentation
- **Flow README:** `flows/README.md`
- **Project Overview:** `docs/PROJECT_OVERVIEW.md`
- **System Diagrams:** `docs/SYSTEM_DIAGRAM.md`

### Scripts
- **Setup:** `ops/scripts/setup-orchestrator.ps1`
- **Deploy:** `ops/scripts/deploy-flows.ps1`
- **Verify:** `ops/scripts/verify-flows.ps1`

---

**Last Updated:** May 17, 2026  
**Version:** 1.0  
**Status:** Ready for Deployment
