# UiPath Builder Agent - Flow Workflows

**Flow-based orchestration workflows for enterprise automation delivery**

---

## Overview

This folder contains **UiPath Flow** workflows that orchestrate the agent system and provide production-ready automation patterns. Flows are JSON-based, integrate with Integration Service, and deploy easily to Orchestrator.

---

## Available Flows

### 1. Enterprise Intake Triage Flow

**Path:** `flows/enterprise-intake-flow/flow.json`

**Purpose:** Routes business intake requests to appropriate handlers and invokes the orchestrator agent

**Flow:**
```
Manual Trigger → Receive Intake → Classify by Business Unit → 
Route to Queue (Finance/HR/Ops/Shared) → Email Notification → 
Invoke Builder Orchestrator → Complete
```

**Key Features:**
- Business unit classification (FINANCE, HR, OPS, default)
- Orchestrator queue routing
- Email notifications via Integration Service
- Agent invocation (builder-orchestrator)
- Structured outputs

**Inputs:**
- `businessUnit` (string): FINANCE, HR, OPS, etc.
- `intakeId` (string): Unique identifier
- `requestSummary` (string): Brief description
- `stakeholders` (array): Email addresses

**Outputs:**
- `status`: "success"
- `intakeId`: Request ID
- `routedTo`: Target queue
- `orchestratorInvoked`: true

---

### 2. Solution Planning & Review Flow

**Path:** `flows/solution-planning-flow/flow.json`

**Purpose:** Orchestrates planning artifact generation and approval workflow

**Flow:**
```
Queue Trigger → Extract Intake → Discovery Agent → 
Solution Architect Agent → Store Artifacts → 
Action Center Approval Task → Evaluate Decision → 
Verifier Agent (if approved) → Email Notifications → Complete
```

**Key Features:**
- Queue-triggered execution
- Multi-agent coordination (discovery → architect → verifier)
- Artifact storage in Orchestrator storage buckets
- Action Center approval with markdown preview
- Decision branching (Approve/Revise/Reject)
- Quality verification before build

**Trigger:**
- Queue: `Q_PLANNING_REQUESTS`

**Agent Invocations:**
1. `discovery-agent` - Context extraction
2. `solution-architect-agent` - Generate spec/plan/tasks
3. `verifier-agent` - Quality validation

**Artifacts Stored:**
- `spec-{intakeId}.md`
- `plan-{intakeId}.md`
- `tasks-{intakeId}.md`

**Outputs:**
- `status`: ready_for_build, verification_blocked, revision_requested, rejected
- `intakeId`: Request ID
- `artifactBucket`: Storage location
- `blockers`: List of issues (if blocked)

---

### 3. Evidence Collection & Deployment Gate Flow

**Path:** `flows/evidence-collection-flow/flow.json`

**Purpose:** Collects validation evidence and controls deployment with automated gates

**Flow:**
```
Manual Trigger → Collect CI/CD Telemetry → Collect Test Results → 
Deployment Evidence Agent → Evaluate Readiness → 
[If Ready] Check Environment → 
[If Prod] Require Approval → Deploy → Smoke Test → 
Email Notifications → Complete
```

**Key Features:**
- CI/CD telemetry collection via HTTP
- Test result retrieval from storage buckets
- Deployment evidence agent validation
- Environment-based routing (dev/test auto-deploy, prod requires approval)
- Action Center approval for production
- Automated smoke testing
- Email notifications for all outcomes

**Inputs:**
- `intakeId` (string): Project identifier
- `projectPath` (string): Path to artifacts
- `environment` (string): dev, test, or prod

**Agent Invocations:**
- `deployment-evidence-agent` - Readiness assessment

**Decision Points:**
1. Readiness: ready, blocked, pending
2. Environment: prod (requires approval), non-prod (auto)
3. Approval: approve, deny
4. Smoke test: pass, fail

**Outputs:**
- `status`: deployed, smoke_test_failed, blocked, pending, denied
- `environment`: Target environment
- `deploymentId`: Job ID (if deployed)
- `smokeTestPassed`: boolean
- `blockers`: List of issues (if blocked)

---

## Flow Architecture

### Integration Points

| Integration | Flow Usage |
|-------------|------------|
| **Orchestrator Queues** | Intake routing, queue triggers |
| **Integration Service** | Email notifications (Outlook connector) |
| **Agent Invocation** | All 5 agents called via agent-invoke nodes |
| **Action Center** | Approval tasks with form fields |
| **Storage Buckets** | Artifact storage and retrieval |
| **HTTP APIs** | External telemetry collection |
| **Orchestrator Processes** | Deployment execution, smoke tests |

### Flow Patterns

**1. Manual → Agent → Queue Pattern** (Enterprise Intake)
```
User Input → Agent Processing → Queue Routing → Notifications
```

**2. Queue → Multi-Agent → Approval Pattern** (Solution Planning)
```
Queue Trigger → Agent Chain → Storage → Human Approval → Verification
```

**3. Evidence → Gate → Deploy Pattern** (Evidence Collection)
```
Collect Evidence → Agent Validation → Environment Check → 
Approval (if prod) → Deploy → Smoke Test
```

---

## Deployment to Orchestrator

### Prerequisites

1. **Orchestrator Setup:**
   - Queues created: `Q_FINANCE_INTAKE`, `Q_HR_INTAKE`, `Q_OPS_INTAKE`, `Q_SHARED_INTAKE`, `Q_PLANNING_REQUESTS`
   - Storage buckets: `planning-artifacts`, `test-results`
   - Processes: `Deploy_Package`, `Smoke_Test_Runner`

2. **Integration Service:**
   - Outlook connector configured
   - Connection created with send-email permissions

3. **Agents Deployed:**
   - `builder-orchestrator`
   - `discovery-agent`
   - `solution-architect-agent`
   - `verifier-agent`
   - `deployment-evidence-agent`

4. **Assets:**
   - `CI_API_TOKEN` (for telemetry collection)

### Deployment Commands

**Option 1: Via Studio Web**
1. Open Studio Web → Flows
2. Import each `flow.json` file
3. Configure Integration Service connections
4. Publish to Orchestrator

**Option 2: Via CLI** (when Flow CLI support is available)
```bash
# Package Flow
uip flow pack flows/enterprise-intake-flow

# Deploy to Orchestrator
uip flow deploy \
  --package enterprise-intake-flow.1.0.0.nupkg \
  --folder Shared \
  --environment Test
```

---

## Testing

### Local Testing

Flows can be tested in Studio Web:
1. Open flow in Studio Web
2. Use "Test Run" with sample inputs
3. Verify decision branches and agent invocations

### Sample Inputs

**Enterprise Intake Flow:**
```json
{
  "businessUnit": "FINANCE",
  "intakeId": "AH-INTAKE-001",
  "requestSummary": "Automate invoice exception handling",
  "stakeholders": ["finance-lead@company.com"]
}
```

**Solution Planning Flow:**
Queue item with:
```json
{
  "businessGoal": "Reduce manual invoice processing",
  "businessUnit": "FINANCE",
  "intakeId": "AH-INTAKE-001",
  "stakeholders": ["finance-lead@company.com"]
}
```

**Evidence Collection Flow:**
```json
{
  "intakeId": "AH-INTAKE-001",
  "projectPath": "/artifacts/invoice-automation",
  "environment": "test"
}
```

---

## Flow Design Principles

### 1. Agent-First Architecture
- Flows orchestrate agents, not replace them
- Agents handle domain logic
- Flows handle integration and routing

### 2. Evidence-Driven Gates
- Every deployment requires evidence
- Evidence collection is automated
- Gates prevent incomplete deployments

### 3. Human-in-the-Loop
- Action Center for critical decisions
- Markdown previews in approval forms
- Clear escalation paths

### 4. Environment Safety
- Non-prod auto-deploys
- Production requires approval + change ID
- Smoke tests always run post-deploy

### 5. Comprehensive Notifications
- Email at every decision point
- Success and failure paths
- Clear next steps in messages

---

## Diagram: Complete Flow System

```
                    ┌─────────────────┐
                    │  User/System    │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   Intake     │ │   Planning   │ │   Evidence   │
    │     Flow     │ │     Flow     │ │     Flow     │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           ▼                ▼                ▼
    ┌──────────────────────────────────────────────┐
    │           Agent System (5 Agents)             │
    │  Orchestrator │ Discovery │ Architect │       │
    │  Verifier │ Deployment Evidence              │
    └──────────────────┬───────────────────────────┘
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  Queues  │ │ Storage  │ │  Action  │
    │          │ │ Buckets  │ │  Center  │
    └──────────┘ └──────────┘ └──────────┘
```

---

## Next Steps

### For Development
1. Test flows in Studio Web
2. Configure Integration Service connections
3. Create Orchestrator queues and storage buckets
4. Deploy agents to Orchestrator

### For Production
1. Create production environment queues
2. Set up monitoring and alerting
3. Configure approval groups in Action Center
4. Establish deployment runbooks

### For Enhancement
1. Add Slack/Teams notifications
2. Integrate with ITSM (ServiceNow, Jira)
3. Add metrics collection
4. Implement retry logic

---

## Related Documentation

- **Agent System:** `../agents/`
- **Studio Web UI:** `../studio/web/`
- **Project Overview:** `../docs/PROJECT_OVERVIEW.md`
- **Deployment Guide:** `../docs/generated/deployment-runbook.md`

---

**Last Updated:** May 17, 2026  
**Flow Version:** 1.0.0  
**Status:** Ready for Deployment
