---
name: uipath-confluence-connector
description: Use when publishing, updating, or troubleshooting Confluence documentation through UiPath Integration Service. TRIGGER: Confluence docs, PDD/SDD publishing, release notes. DO NOT TRIGGER: direct Atlassian API tokens or non-UiPath Confluence automation.
---

# UiPath Confluence Connector

Use UiPath Integration Service Confluence connections to publish project documentation without
handling Atlassian credentials directly.

## When to Use

- Publish or update PDD, SDD, ADD, release notes, runbooks, or evaluation reports in Confluence.
- Build a UiPath workflow or agent step that writes documentation to Confluence.
- Troubleshoot Confluence connector authentication, permission, scope, or page update failures.
- Sync local markdown or generated documentation into a Confluence space.

## Critical Rules

1. Use UiPath connector authentication. Do not use Basic Auth, Atlassian PATs, or copied OAuth
   tokens unless the user explicitly approves a temporary diagnostic fallback.
2. Never log, paste, or commit access tokens, connection IDs from private tenants, cookies, or
   authorization headers.
3. Resolve the target space and page before writing. For updates, read the current page version
   first and increment it exactly once.
4. Convert markdown to Confluence-compatible storage XHTML before publishing.
5. Test with one page before bulk publishing or updating a documentation tree.

## Workflow

1. Confirm the target Confluence site, space, parent page, and desired action: create, update, or
   attach files.
2. Confirm UiPath Automation Cloud authentication is available:

```powershell
uipath auth --tenant <TENANT_NAME>
```

3. Confirm a UiPath Integration Service connection exists for Atlassian Confluence and record the
   connection identifier in a local, gitignored config source.
4. For updates, find the page by space and title or page ID, then read the latest version number.
5. Convert content to storage XHTML. Upload images as page attachments and reference them from the
   page body.
6. Create or update the page through the connector-backed request path.
7. Verify the returned page ID, version, and browser URL before reporting success.

## Request Patterns

Use these Confluence Cloud API shapes through the UiPath connector-backed HTTP action or approved
project API route.

```http
GET /wiki/api/v2/pages?spaceId=<SPACE_ID>&title=<PAGE_TITLE>
```

```http
POST /wiki/api/v2/pages
Content-Type: application/json
```

```json
{
  "spaceId": "<SPACE_ID>",
  "status": "current",
  "title": "<PAGE_TITLE>",
  "parentId": "<PARENT_PAGE_ID>",
  "body": {
    "representation": "storage",
    "value": "<p>HTML content</p>"
  }
}
```

```http
PUT /wiki/api/v2/pages/<PAGE_ID>
Content-Type: application/json
```

```json
{
  "id": "<PAGE_ID>",
  "status": "current",
  "title": "<PAGE_TITLE>",
  "version": {
    "number": 2
  },
  "body": {
    "representation": "storage",
    "value": "<p>Updated HTML content</p>"
  }
}
```

## Content Notes

- Use Confluence storage format for rich content.
- Publish Mermaid as a fenced code block unless the target Confluence space has a Mermaid macro.
- Upload local images first; Confluence cannot render `localhost` or workspace-local file paths.
- Keep generated pages deterministic so future updates produce minimal diffs.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `Unauthorized` or `scope does not match` | Reauthorize the UiPath Integration Service connection with Confluence scopes. |
| `space not found` | Confirm `SPACE_ID`, permissions, and site selection. |
| Update conflict | Re-read the page and retry with the latest version number. |
| Images missing | Confirm attachments were uploaded and referenced by attachment filename. |

## Anti-Patterns

- Storing Atlassian credentials in `.env` when a UiPath connector is available.
- Updating pages without reading the current version.
- Publishing raw markdown as storage XHTML.
- Bulk-updating a Confluence space before a single-page smoke test.
