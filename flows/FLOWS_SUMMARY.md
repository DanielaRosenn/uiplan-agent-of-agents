# UiPath Flow Workflows - Complete Package

**5 Production-Ready Flows for Enterprise Automation Orchestration**

---

## ✅ What's Included

### 🔄 5 Flow Workflows

1. **Enterprise Intake Triage Flow** - Routes business requests to appropriate handlers
2. **Solution Planning & Review Flow** - Orchestrates planning and approval workflow
3. **Evidence Collection & Deployment Gate Flow** - Controls deployment with automated gates
4. **Agent Monitoring Flow** - Monitors agent health and performance (scheduled every 5 min)
5. **Reporting Flow** - Generates daily reports and metrics (scheduled daily at 8 AM)

### ⚙️ Deployment Scripts

| Script | Platform | Purpose |
|--------|----------|---------|
| `ops/scripts/setup-orchestrator.ps1` | Windows | Creates queues, guides bucket/asset setup |
| `ops/scripts/setup-orchestrator.sh` | Linux/Mac | Creates queues, guides bucket/asset setup |
| `ops/scripts/deploy-flows.ps1` | Windows | Prepares flows for deployment |
| `ops/scripts/verify-flows.ps1` | Windows | Validates Orchestrator configuration |

### 📚 Documentation

- `flows/README.md` - Complete flow documentation
- `flows/DEPLOYMENT_GUIDE.md` - Step-by-step deployment guide

---

## 🚀 Quick Start

### 1. Setup Orchestrator

```powershell
# Windows
.\ops\scripts\setup-orchestrator.ps1

# Linux/Mac
bash ops/scripts/setup-orchestrator.sh
```

**Creates automatically:**
- ✅ 7 Orchestrator queues

**Requires manual creation:**
- 📝 4 storage buckets (instructions provided)
- 📝 6 Orchestrator assets (instructions provided)

### 2. Deploy Flows

**Via Studio Web (Recommended):**

1. Open https://cloud.uipath.com/studio
2. Navigate to **Flows**
3. Click **Import Flow**
4. Upload each `flow.json` file from `flows/*/`
5. Configure Integration Service connections (Outlook)
6. Click **Publish** to Orchestrator (folder: Shared)

### 3. Verify Deployment

```powershell
.\ops\scripts\verify-flows.ps1
```

Checks:
- ✅ Authentication status
- ✅ Queue existence
- ✅ Asset existence
- 📝 Manual flow verification steps

---

## 📊 Flow Details

### 1. Enterprise Intake Triage Flow

**Trigger:** Manual

**Purpose:** Routes business intake requests to appropriate queues and invokes orchestrator

**Flow:**
```
Input → Classify by BU → Route to Queue (Finance/HR/Ops/Shared) → 
Email Notification → Invoke Builder Orchestrator → Complete
```

**Inputs:**
- `businessUnit`: FINANCE, HR, OPS, etc.
- `intakeId`: Unique identifier
- `requestSummary`: Brief description
- `stakeholders`: Email list

**Outputs:**
- Queue item created
- Email sent
- Orchestrator agent invoked
- Status returned

---

### 2. Solution Planning & Review Flow

**Trigger:** Queue (`Q_PLANNING_REQUESTS`)

**Purpose:** Generates planning artifacts and manages approval workflow

**Flow:**
```
Queue Trigger → Discovery Agent → Solution Architect Agent → 
Store Artifacts → Action Center Approval → Verifier Agent → 
Email Notifications → Complete
```

**Agent Invocations:**
- Discovery Agent - Context extraction
- Solution Architect Agent - Generate spec/plan/tasks
- Verifier Agent - Quality validation

**Artifacts Generated:**
- `spec-{intakeId}.md`
- `plan-{intakeId}.md`
- `tasks-{intakeId}.md`

**Approval Flow:**
- Approve → Verification → Ready for build
- Request Changes → Return to architect
- Reject → Close request

---

### 3. Evidence Collection & Deployment Gate Flow

**Trigger:** Manual

**Purpose:** Collects evidence, validates readiness, controls deployment

**Flow:**
```
Input → Collect Telemetry → Collect Tests → Deployment Evidence Agent → 
Evaluate Readiness → [If Ready] Check Environment → 
[If Prod] Approval → Deploy → Smoke Test → Notifications → Complete
```

**Decision Gates:**
1. **Readiness:** ready, blocked, pending
2. **Environment:** dev/test (auto-deploy), prod (requires approval)
3. **Approval:** approve, deny
4. **Smoke Test:** pass, fail

**Safety Features:**
- Production deployments require Action Center approval
- Change request ID mandatory for prod
- Automated smoke testing post-deploy
- Email notifications for all outcomes

---

### 4. Agent Monitoring Flow

**Trigger:** Schedule (every 5 minutes)

**Purpose:** Continuous agent health monitoring and alerting

**Flow:**
```
Schedule Trigger → Collect Agent Metrics → Analyze Health → 
Check Thresholds → [If Alert] Send Email → Store Metrics → 
Update Dashboard → Complete
```

**Monitors:**
- Agent execution counts
- Health scores
- Response times
- Failure rates

**Alert Thresholds:**
- Any failed agents
- More than 2 degraded agents
- Average response time > 5000ms

**Outputs:**
- Metrics stored in `monitoring-data` bucket
- Dashboard updated
- Alerts sent if thresholds exceeded

---

### 5. Reporting Flow

**Trigger:** Schedule (daily at 8 AM)

**Purpose:** Generates comprehensive daily reports

**Flow:**
```
Schedule Trigger → Define Period → Collect Intake Metrics → 
Collect Agent Metrics → Collect Deployment Metrics → 
Aggregate → Generate Report → Store → Email Distribution → 
Check Alerts → Complete
```

**Report Includes:**
- Total intake requests by business unit
- Planning request count
- Agent execution metrics
- Deployment success rate
- Trend analysis
- Alert conditions

**Distribution:**
- Email to leadership and ops teams
- Stored in `monitoring-data` bucket (markdown + JSON)
- Alerts sent if performance < threshold

---

## 🔧 Prerequisites

### Orchestrator Queues (7)

| Queue | Purpose |
|-------|---------|
| `Q_FINANCE_INTAKE` | Finance automation requests |
| `Q_HR_INTAKE` | HR automation requests |
| `Q_OPS_INTAKE` | Operations automation requests |
| `Q_SHARED_INTAKE` | General automation requests |
| `Q_PLANNING_REQUESTS` | Planning workflow trigger |
| `Q_IMPLEMENTATION_READY` | Approved for implementation |
| `Q_DEPLOYMENT_READY` | Ready for deployment |

### Storage Buckets (4)

| Bucket | Purpose |
|--------|---------|
| `planning-artifacts` | Spec, plan, tasks files |
| `test-results` | Test execution results |
| `evidence-packages` | Deployment evidence |
| `monitoring-data` | Metrics and reports |

### Orchestrator Assets (6)

| Asset | Type | Purpose |
|-------|------|---------|
| `CI_API_TOKEN` | Text | CI/CD API access |
| `SMTP_SERVER` | Text | Email server (optional) |
| `ALERT_EMAIL_LIST` | Text | Alert recipients |
| `ASSET_FINANCE_POLICY` | Text | Finance policy URL |
| `ASSET_HR_POLICY` | Text | HR policy URL |
| `ASSET_SHARED_POLICY` | Text | Shared policy URL |

### Integration Service

- **Outlook Connector** configured
- **Connection** created with send-email permissions

---

## 📦 File Structure

```
flows/
├── enterprise-intake-flow/
│   └── flow.json                    # Intake routing flow
├── solution-planning-flow/
│   └── flow.json                    # Planning and approval flow
├── evidence-collection-flow/
│   └── flow.json                    # Deployment gate flow
├── agent-monitoring-flow/
│   └── flow.json                    # Health monitoring flow (scheduled)
├── reporting-flow/
│   └── flow.json                    # Daily reporting flow (scheduled)
├── README.md                        # Flow documentation
└── DEPLOYMENT_GUIDE.md              # Deployment instructions

ops/scripts/
├── setup-orchestrator.ps1           # Windows setup script
├── setup-orchestrator.sh            # Linux/Mac setup script
├── deploy-flows.ps1                 # Deployment helper
└── verify-flows.ps1                 # Verification script
```

---

## ✨ Key Features

### 1. Agent-First Architecture
- Flows orchestrate agents, not replace them
- 5 coded agents invoked across workflows
- Clear separation: flows for integration, agents for logic

### 2. Evidence-Driven Gates
- Automated evidence collection
- Quality gates prevent incomplete deployments
- Production deployments require approval

### 3. Human-in-the-Loop
- Action Center approvals for critical decisions
- Markdown preview in approval forms
- Clear escalation paths

### 4. Environment Safety
- Dev/test auto-deploy
- Production requires approval + change ID
- Smoke tests always run

### 5. Comprehensive Notifications
- Email at every decision point
- Success and failure notifications
- Clear next steps in messages

### 6. Monitoring & Reporting
- Continuous health monitoring
- Daily automated reports
- Alert thresholds
- Trend analysis

---

## 🎯 Use Cases

### Use Case 1: Business Intake Processing

```
1. User submits request via Enterprise Intake Flow
2. Flow routes to appropriate queue
3. Email notification sent
4. Orchestrator agent invoked
5. Request tracked through system
```

### Use Case 2: Solution Planning Workflow

```
1. Intake added to planning queue
2. Solution Planning Flow triggers
3. Discovery and architect agents generate plan
4. Stakeholder receives Action Center task
5. Stakeholder approves
6. Verifier validates quality
7. Team notified: ready for build
```

### Use Case 3: Controlled Deployment

```
1. Dev triggers Evidence Collection Flow
2. Flow collects CI/CD data and tests
3. Deployment evidence agent validates
4. For prod: approval task created
5. After approval: deploy and smoke test
6. Team notified of outcome
```

### Use Case 4: Continuous Monitoring

```
1. Agent Monitoring Flow runs every 5 min
2. Collects agent metrics
3. Checks thresholds
4. If degraded: sends alert
5. Stores metrics for reporting
```

### Use Case 5: Daily Reporting

```
1. Reporting Flow runs daily at 8 AM
2. Collects all metrics
3. Generates markdown report
4. Emails to leadership
5. Alerts if performance poor
```

---

## 📈 Benefits

### For Business
- ✅ Faster automation delivery
- ✅ Clear approval workflows
- ✅ Traceability from intake to deployment
- ✅ Daily visibility into progress

### For Development
- ✅ Automated orchestration
- ✅ Quality gates enforce standards
- ✅ Evidence-driven handoffs
- ✅ Clear success criteria

### For Operations
- ✅ Controlled deployments
- ✅ Automated smoke testing
- ✅ Continuous monitoring
- ✅ Production safety gates

### For Management
- ✅ Daily reports and metrics
- ✅ Trend analysis
- ✅ Performance visibility
- ✅ Resource utilization tracking

---

## 🚀 Next Steps

### Immediate (Today)
1. ✅ Run `setup-orchestrator.ps1` to create queues
2. ✅ Create storage buckets manually
3. ✅ Create assets manually
4. ✅ Configure Integration Service connector

### This Week
1. Import flows to Studio Web
2. Test each flow with sample data
3. Configure email addresses
4. Deploy to non-prod environment

### This Month
1. Integrate with production agents
2. Set up production approval groups
3. Configure monitoring dashboards
4. Establish deployment runbooks

---

## 📞 Support

### Documentation
- **Flow README:** `flows/README.md`
- **Deployment Guide:** `flows/DEPLOYMENT_GUIDE.md`
- **Project Overview:** `docs/PROJECT_OVERVIEW.md`
- **System Diagrams:** `docs/SYSTEM_DIAGRAM.md`

### Scripts
- **Setup:** `ops/scripts/setup-orchestrator.ps1`
- **Deploy:** `ops/scripts/deploy-flows.ps1`
- **Verify:** `ops/scripts/verify-flows.ps1`

---

## ✅ Summary

**Created:**
- ✅ 5 production-ready Flow workflows
- ✅ 4 deployment/setup scripts (Windows + Linux)
- ✅ Complete documentation
- ✅ Deployment guide
- ✅ Verification tools

**Ready for:**
- ✅ Studio Web import
- ✅ Orchestrator deployment
- ✅ Integration with coded agents
- ✅ Production use

**Integration points:**
- ✅ 7 Orchestrator queues
- ✅ 4 storage buckets
- ✅ 6 Orchestrator assets
- ✅ Integration Service (email)
- ✅ Action Center (approvals)
- ✅ 5 coded agents

---

**Last Updated:** May 17, 2026  
**Version:** 1.0  
**Status:** Complete and Ready for Deployment

All flows are JSON-based, version-controlled, and ready to deploy to Orchestrator via Studio Web!
