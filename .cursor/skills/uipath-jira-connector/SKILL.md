---
name: uipath-jira-connector
description: Use when creating, updating, searching, or troubleshooting Jira issues through UiPath Integration Service. TRIGGER: sync tasks to Jira, update issue status, bulk-create issues. DO NOT TRIGGER: drafting ticket content only or direct Atlassian PAT automation.
---

# UiPath Jira Connector

Use UiPath Integration Service Jira connections for issue operations without storing direct
Atlassian credentials in the project.

## When to Use

- Create Jira issues from implementation tasks, plan items, or discovered follow-up work.
- Update Jira issue status, labels, links, comments, or documentation references during development.
- Bulk-create stories, tasks, bugs, or subtasks from approved requirements.
- Troubleshoot UiPath connector authentication, scope, permission, or field mapping failures.

## Critical Rules

1. Ask before creating or updating live Jira issues unless the user already requested that action.
2. Prefer UiPath Integration Service connector auth. Do not use Basic Auth or Atlassian PATs without
   explicit user approval.
3. Never expose tokens, connector secrets, cookies, authorization headers, or private issue payloads.
4. Make issue creation idempotent where possible: search for an existing issue before creating a
   duplicate.
5. For status changes, verify the target transition exists for the current workflow state.
6. Return created or updated issue keys and browse URLs to the user.

## Workflow

1. Confirm the Jira project key, issue type, target action, and whether the action should be live or
   draft-only.
2. Authenticate with UiPath if needed:

```powershell
uipath auth --tenant <TENANT_NAME>
```

3. Confirm a Jira-capable Atlassian connection exists in UiPath Integration Service.
4. For creates, search by summary, labels, or external reference before writing.
5. Map required Jira fields for the target project: summary, description, issue type, parent/epic,
   labels, components, priority, and custom fields.
6. Execute the connector-backed create, update, transition, or comment operation.
7. Verify the response contains the expected issue key, status, and URL.

## Common Operations

| Operation | Required Inputs | Validation |
| --- | --- | --- |
| Create issue | project key, issue type, summary, description | Search first to avoid duplicates. |
| Add comment | issue key, comment body | Confirm issue exists and user has browse permission. |
| Transition issue | issue key, target status | List available transitions first. |
| Link docs | issue key, Confluence/page URL | Add a comment or remote link, based on project convention. |
| Bulk create | approved issue list, parent mapping | Dry-run the payload summary before writing. |

## Payload Shape

Use the project-approved connector route or UiPath activity for the actual call. Keep payloads
explicit and minimal.

```json
{
  "projectKey": "<PROJECT_KEY>",
  "issueType": "Task",
  "summary": "Update deployment checklist documentation",
  "description": "Document the deployment smoke-test steps and link the generated Confluence page.",
  "labels": ["documentation", "uipath"],
  "components": ["Builder Agent"]
}
```

## Development Task Sync

When syncing development work to Jira:

1. Link the implementation plan, branch, PR, or relevant docs.
2. Add concise progress comments only when they add signal: completed milestone, blocker, decision,
   verification result, or requested review.
3. Do not spam Jira with every local edit or transient test failure.
4. Use clear status language: `In Progress`, `Blocked`, `In Review`, `Done`, or the project-specific
   workflow status.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `Failed to retrieve connector token` | UiPath auth, tenant, connection ID, and Integration Service permissions. |
| `scope does not match` | Reauthorize the connector with Jira scopes. |
| Required field error | Fetch create metadata for the project and issue type. |
| Transition fails | List available transitions from the issue's current status. |
| Epic or parent link missing | Confirm the project uses team-managed or company-managed field conventions. |

## Anti-Patterns

- Creating live Jira issues from an unreviewed draft.
- Hardcoding project keys, custom field IDs, tenant URLs, or connection IDs in the skill.
- Using localhost-only project endpoints in reusable skill instructions.
- Updating Jira for noisy intermediate development states.
