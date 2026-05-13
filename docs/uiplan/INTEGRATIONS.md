# UiPlan Studio: Integration & Orchestrator Visualization

## Overview

UiPlan Studio automatically extracts and visualizes external integrations and Orchestrator resources from your RPA project. This gives you instant visibility into:

- What external systems your automation connects to
- Which Orchestrator platform features it uses
- How workflows orchestrate across systems

## What Gets Detected

### External Integrations

The indexer scans XAML workflow files for these patterns:

| Pattern | Detected As | Examples |
|---------|-------------|----------|
| `Salesforce.*Activity` | Salesforce | Create Object, Query Records, Update Record |
| `Slack.*Activity` | Slack | Post Message, Create Channel, Upload File |
| `ZenDesk.*Activity` | ZenDesk | Create Ticket, Update Status, Search Tickets |
| `HTTP Request`, `HttpClient` | HTTP API | REST calls, webhooks, external APIs |
| `Send Mail`, `SMTP` | Email | Notification emails, FYI messages |
| `Integration Service`, `IntegrationService` | Integration Service | Connector-based integrations |
| `webhook`, `Webhook` | Webhook | Incoming webhook handlers |

### Orchestrator Resources

The indexer scans for Orchestrator platform activities:

| Pattern | Detected As | Examples |
|---------|-------------|----------|
| `Add Queue Item`, `Get Transaction Item`, `Set Transaction Status` | Queue | Dispatcher-Performer pattern |
| `Get Asset`, `Get Credential` | Asset | Configuration values, credentials |
| `Storage Bucket` | Storage Bucket | Large file storage |
| `Action Center`, `Create Form Task` | Action Center | Human-in-the-loop approvals |
| `Get Robot Credential`, `Robot` | Robot | Robot orchestration |

## How It Appears

### In Focus Mode (Default)

1. **Entry point only** (Main-Queue.xaml): Green MAIN badge, chevron indicator (►)
2. **Double-click to expand**: See all invoked workflows + integrations + Orchestrator resources
3. **Visual coding**:
   - **Red nodes**: External integrations (Salesforce, HTTP API, Email, etc.)
   - **Gray nodes**: Orchestrator resources (Queue, Asset, Action Center)
   - **Green nodes**: RPA workflows
   - **Purple nodes**: Skills
   - **Teal nodes**: UiPlan bundles
4. **Dashed "uses" edges**: Connect workflows to integrations/resources

### Example: Sales Renewal Price Commitment

The demo project shows:

- **Main-Queue.xaml** (entry point)
  - → **Queue** (Get Transaction Item from Orchestrator)
  - → **Asset** (Config values from Orchestrator)
  - → **Action Center** (HITL approval task creation)
  - → **Email** (Send FYI email)
  - → **Salesforce** (Update opportunity record)
  - → **HTTP API** (Webhook callback)
  - → **ApprovalFlow_SalesRep.xaml** (invoked workflow)
  - → **ApprovalFlow_Manager.xaml** (invoked workflow)
  - ... (more approval flows)

## Technical Details

### Backend Implementation

**File**: `studio/api/app/explorer_indexer.py`

**Function**: `_extract_integrations(text: str) -> dict[str, list[str]]`

```python
def _extract_integrations(text: str) -> dict[str, list[str]]:
    """Extract external integrations and Orchestrator resources from XAML."""
    integrations: dict[str, list[str]] = {
        "external": [],
        "orchestrator": [],
    }
    # ... regex pattern matching ...
    return integrations
```

The function is called during XAML indexing and adds child nodes to the workflow:

```python
# In _index_file function
if suffix == ".xaml" and text:
    integrations = _extract_integrations(text)
    
    # Add external integrations as child nodes
    for ext in integrations["external"]:
        child_id = f"{node_id}::ext-{ext.lower().replace(' ', '-')}"
        children_nodes.append({
            "id": child_id,
            "label": ext,
            "kind": "external",
            "layer": "external",
            "desc": f"External integration: {ext}",
        })
        # ... add "uses" edge ...
    
    # Add Orchestrator resources as child nodes
    for orch in integrations["orchestrator"]:
        child_id = f"{node_id}::orch-{orch.lower().replace(' ', '-')}"
        children_nodes.append({
            "id": child_id,
            "label": orch,
            "kind": "orchestrator_resource",
            "layer": "orchestrator",
            "desc": f"Orchestrator resource: {orch}",
        })
        # ... add "uses" edge ...
```

### Frontend Styling

**File**: `studio/web/src/theme.ts`

```typescript
export const LAYERS: Record<LayerKey, LayerInfo> = {
  // ...
  external:     { name: "external",     color: "#dc2626", soft: "#fee2e2", short: "EXT", Icon: Cloud },
  orchestrator: { name: "orchestrator", color: "#475569", soft: "#e2e8f0", short: "ORC", Icon: Server },
  // ...
};

export const KIND_ICONS: Record<string, IconCmp> = {
  // ...
  external: Cloud,                    // External integrations
  orchestrator_resource: Server,      // Orchestrator resources
  // ...
};

export const EDGE_STYLE: Record<EdgeKind, EdgeStyle> = {
  // ...
  uses: { color: "#dc2626", dash: "2 2", width: 1.6, label: "uses" },
  // ...
};
```

## Benefits

### For Business Analysts
- **Instant dependency map**: See what systems are involved without reading code
- **Risk assessment**: Identify external dependencies that could fail
- **Stakeholder communication**: Show integration points in process diagrams

### For Developers
- **Architecture review**: Validate integration patterns across workflows
- **Refactoring**: Identify duplicate integration logic to consolidate
- **Testing scope**: Know which external systems to mock/stub

### For Operations
- **Orchestrator resource inventory**: See which queues, assets, buckets are used
- **Platform dependencies**: Understand which Orchestrator features are critical
- **Deployment planning**: Ensure Orchestrator resources exist before deploy

## Extending Detection

To add a new integration pattern:

1. Edit `studio/api/app/explorer_indexer.py`
2. Add a new pattern tuple to `external_patterns` or `orch_patterns`:
   ```python
   external_patterns = [
       # ... existing patterns ...
       (r'MySystem[^"<>]*Activity', "MySystem"),
   ]
   ```
3. Regenerate the demo fixture: `python regenerate_integrations_demo.py`
4. Rebuild the frontend: `npm run build`

## See Also

- `docs/uiplan/VIEW_MODES.md` - How to expand nodes in Focus Mode
- `docs/uiplan/STUDIO.md` - Full UiPlan Studio user guide
- `docs/DEMO_FIXTURE_HOWTO.md` - How to create demo data from real projects
