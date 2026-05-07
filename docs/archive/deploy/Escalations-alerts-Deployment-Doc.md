# Deployment Documentation

**Process Name**: Escalations alerts  
**Version**: 1.0.0  
**Deployment Date**: 2026-05-04  
**Deployed By**: Daniela Rosenstein / UiPath Automation Team  
**Environment**: TEST  
**Related Documents**: [PDD](../pdd/Escalations-alerts-PDD.md)

---

## 1. Deployment Overview

### 1.1 Deployment Summary

**Purpose**: Deploy and validate the Escalations alerts process that listens to escalation
emails and sends Slack notifications with Zendesk ticket context when available.

**Deployment Type**: Initial Deployment

**Change Description**:
- New event-triggered process based on Office 365 `NewEmailReceived`.
- Added escalation routing check based on CC alias.
- Added ticket-id parsing logic and Slack alert webhook integration.

**Expected Downtime**: None

**Deployment Window**: Business hours TEST deployment window

### 1.2 Deployment Scope

**Components Being Deployed**:
- [x] UiPath Process Package
- [x] Orchestrator Configuration
- [ ] Database Changes
- [ ] Custom Libraries/Activities
- [x] Configuration Files
- [ ] Supporting Scripts

**Environments**:
- [ ] Development (DEV)
- [x] Testing (TEST)
- [ ] User Acceptance Testing (UAT)
- [ ] Production (PROD)

### 1.3 Deployment Team

| Role | Name | Contact | Responsibility |
|------|------|---------|----------------|
| Deployment Lead | Daniela Rosenstein | Internal | Overall coordination |
| RPA Developer | UiPath Automation Team | Internal | Package deployment |
| Infrastructure Admin | TBD | TBD | Robot/runtime configuration |
| Database Admin | N/A | N/A | No DB changes |
| Application Support | Support Management | escalations@catonetworks.com | Access verification |
| Business Stakeholder | Support Leaders | Slack `@support-leaders` | Functional sign-off |

---

## 2. Pre-Deployment Checklist

### 2.1 Prerequisites

**Required Access**:
- [x] UiPath Orchestrator admin/deployment access (TEST)
- [ ] Robot machine admin access (not required for cloud trigger-only checks)
- [ ] Database access (not applicable)
- [x] Application credentials (Office 365 + Slack webhook)
- [x] Network/firewall access for webhook endpoint
- [x] Source control system access

**Required Artifacts**:
- [ ] UiPath package (.nupkg) - Version: 1.0.0
- [x] Configuration references (Office 365 connection, Slack endpoint)
- [ ] Database scripts (not applicable)
- [ ] Custom activities/libraries (not applicable)
- [x] Documentation (PDD, Deployment Doc)
- [ ] Test results and sign-off (pending execution approval)

**Verification Steps**:
- [x] Workflow logic reviewed from exported process
- [ ] Unit/integration tests recorded in this deployment cycle
- [ ] UAT sign-off received
- [x] Backup plan documented
- [x] Rollback plan documented

### 2.2 Environment Validation

**Target Environment**: TEST

**Orchestrator Details**:
- **URL**: `https://cloud.uipath.com/catonetworks`
- **Version**: Cloud managed (current tenant runtime)
- **Tenant**: `Test`
- **Folder**: `daniela.rosenstein@catonetworks.com's workspace` (or target TEST folder)

**Robot/Runtime Details**:
- **Robot Type**: Unattended/serverless trigger runtime
- **Machine Name**: TBD by folder setup
- **License Type**: Per tenant allocation
- **Number of Robots**: 1 minimum runtime for deployment validation

**System Requirements Check**:
- [x] UiPath cloud connectivity verified
- [x] Required dependencies present in project
- [x] Office 365 trigger connection configured
- [x] Slack endpoint reachable from runtime

### 2.3 Application Access Verification

**Applications to Verify**:

| Application | Version | URL/Path | Test Credential | Status |
|-------------|---------|----------|-----------------|--------|
| Microsoft Office 365 | SaaS | Connection Service | `UIPATH_CATO_ROBOT_PROD@catonetworks.com` | Connected |
| Slack | SaaS | Integration Service connector | `supporty #3` (`supporty_2`) | Connected |
| Slack Incoming Webhook | SaaS | hooks.slack.com | Webhook URL/path | Pending runtime validation |
| Zendesk (link generation only) | SaaS | catonetworks.zendesk.com | N/A | Pending |

**Connector Evidence (Screenshots)**:

**Microsoft Office 365 connection (Connected)**  
![Office 365 connector connected](C:/Users/DanielaRosenstein/.cursor/projects/c-Users-DanielaRosenstein-projects-uipath-builder-agent/assets/c__Users_DanielaRosenstein_AppData_Roaming_Cursor_User_workspaceStorage_1ff22818f14731ac674970b32084d341_images_image-e090abbe-030d-4f19-90a3-47148a4908f6.png)

**Slack connection (Connected)**  
![Slack connector connected](C:/Users/DanielaRosenstein/.cursor/projects/c-Users-DanielaRosenstein-projects-uipath-builder-agent/assets/c__Users_DanielaRosenstein_AppData_Roaming_Cursor_User_workspaceStorage_1ff22818f14731ac674970b32084d341_images_image-4e46529b-7016-4295-9261-8cdf352f4596.png)

### 2.4 Backup and Recovery

**Backup Items**:
- [x] Exported solution copy retained locally
- [x] Current process definition retained (`Main.xaml`, `project.json`)
- [x] Documentation snapshot stored in repo

**Backup Locations**:
- **Package Backup**: `generated/studio-web-read/studio-solution-003c0f7e/`
- **Config Backup**: Orchestrator connection definitions (tenant-managed)
- **Database Backup**: N/A

**Recovery Test**:
- [ ] Rollback test in lower env (pending)
- [ ] Estimated rollback time: 10-20 minutes

---

## 3. Environment Setup

### 3.1 Orchestrator Configuration

#### Step 1: Verify Folder and Permissions

**Path**: `Test tenant -> target workspace/folder`

Minimum permissions required for deployment account:
- View packages/processes
- Create/update process
- Execute jobs
- View logs

#### Step 2: Verify Assets/Connections

| Item | Type | Value/Description | Scope | Notes |
|------|------|-------------------|-------|-------|
| Office 365 Mail Connection | Integration Service | `UIPATH_CATO_ROBOT_PROD@catonetworks.com` | Folder-scoped | Connected |
| Slack Connection | Integration Service | `supporty #3` (resource `supporty_2`) | Folder-scoped | Connected |
| Slack Webhook Endpoint | HTTP/webhook config | Slack alert destination | Folder/global | Should be externalized/secured |
| Escalation Alias | Config text | `escalations@catonetworks.com` | Process config | Routing condition |

#### Step 3: Trigger Setup

Because process uses event-driven email trigger:
1. Ensure `NewEmailReceived` trigger connection is active.
2. Confirm monitored folder is Inbox.
3. Validate event binding fields (`UiPathEvent*`) are populated at runtime.

### 3.2 Runtime Setup

1. Verify runtime availability in target folder.
2. Ensure runtime can access:
   - Office 365 via Integration Service
   - Slack webhook endpoint over HTTPS
3. Confirm logging is enabled and accessible in Orchestrator.

### 3.3 Network and Security Configuration

**Outbound Rules Required**:

| Destination | Port | Protocol | Purpose |
|-------------|------|----------|---------|
| cloud.uipath.com | 443 | HTTPS | Orchestrator + Integration Service |
| hooks.slack.com | 443 | HTTPS | Slack alert delivery |
| catonetworks.zendesk.com | 443 | HTTPS | Ticket URL reference (link only) |

**Security Notes**:
- Move raw webhook URL to secure asset/connection in subsequent hardening pass.
- Avoid logging sensitive email body content in production if policy requires masking.

---

## 4. Deployment Steps

### 4.1 Package Deployment

1. Run build gate in local/project pipeline:
   - restore
   - analyze (must pass with zero errors)
   - test (minimum smoke)
2. Pack process package.
3. Upload package to TEST Orchestrator feed.
4. Create/update process entry:
   - Process Name: `Escalations alerts`
   - Entry Point: `Main.xaml`
   - Version: `1.0.0`

### 4.2 Trigger/Execution Configuration

1. Validate event trigger is enabled.
2. Confirm runtime target and folder selection.
3. Confirm no conflicting legacy trigger remains enabled.

### 4.3 Alert Configuration

| Alert Type | Condition | Recipients | Notification Method |
|------------|-----------|------------|---------------------|
| Job Failure | Any failed execution | Automation + support owners | Orchestrator alerts |
| Slack Delivery Issue | Non-2xx webhook response | Automation team | Log monitoring + alerting |

---

## 5. Deployment Verification

### 5.1 Smoke Tests

1. Send test escalation email with CC `escalations@catonetworks.com` and subject
   `Support #12345`.
   - Expected: Slack alert with valid ticket link.
2. Send escalation CC email without ticket pattern.
   - Expected: fallback "unknown ticket" alert.
3. Send non-escalation email (without required CC).
   - Expected: behavior matches configured fallback branch.

### 5.2 Configuration Validation

- [ ] Process version is correct in Orchestrator
- [ ] Trigger is active
- [ ] Office 365 connection healthy
- [ ] Slack delivery successful
- [ ] Logs visible and complete

### 5.3 Performance Validation

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Event-to-alert latency | < 1 minute | TBD | Pending |
| Success rate | >= 95% on smoke batch | TBD | Pending |

---

## 6. Post-Deployment Activities

1. Share deployment notes with Support Management.
2. Confirm monitoring ownership and escalation path.
3. Document open hardening items:
   - secure webhook storage
   - explicit retry/error handling
   - log data minimization review

---

## 7. Rollback Procedure

### 7.1 Rollback Triggers
- Repeated Slack delivery failures
- Trigger malfunction causing false/missed alerts
- Critical runtime faults

### 7.2 Rollback Steps
1. Disable process trigger immediately.
2. Revert process package to last known good version.
3. Re-validate smoke test with prior version.
4. Notify stakeholders of rollback completion.

Estimated rollback time: 10-20 minutes.

---

## 8. Troubleshooting

| Issue | Possible Cause | Resolution |
|-------|---------------|------------|
| No trigger execution | Connection or folder binding issue | Revalidate Integration Service trigger connection |
| Slack alert missing | Webhook/network failure | Check response code in logs, retest endpoint |
| Ticket id missing unexpectedly | Subject format changed | Update regex or upstream subject convention |

---

## 9. Deployment Sign-Off

| Role | Name | Date | Status | Comments |
|------|------|------|--------|----------|
| Deployment Lead | Daniela Rosenstein | TBD | Pending | |
| Technical Lead | TBD | TBD | Pending | |
| Business Owner | Support Management | TBD | Pending | |

**Overall Status**: Pending approval and execution

---

## 10. Appendix

### A. Key Identifiers
- Process ID: `bf1a7e3f-cd91-42d5-a8f2-1ec7047a952d`
- Solution ID: `003c0f7e-9045-486f-c3bc-08de8671d449`
- Main workflow: `Main.xaml`

### B. Related Documentation
- `docs/pdd/Escalations-alerts-PDD.md`

---

**Document End**
