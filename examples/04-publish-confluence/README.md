# Example 04 — Publish docs to Confluence via UiPath

**Goal:** the agent that builds UiPath projects also publishes its own docs. This example is a UiPath coded workflow that reads the Markdown drafts in [docs/wiki/](../../docs/wiki/) and publishes them to the [Cato RPA Confluence space](https://catonetworks.atlassian.net/wiki/spaces/RPA/overview) through the UiPath Integration Service's Atlassian Confluence connector.

A Python alternative also exists — see [ops/scripts/publish_confluence.py](../../ops/scripts/publish_confluence.py) — for cases where running a full UiPath pack/run is overkill. Both paths authenticate the same way: via the UiPath Integration Service Atlassian Confluence connection. The Python path uses the Integration Service as a proxy (no standalone Atlassian token is ever held on the developer machine). Both publish the same two pages, read from the same Markdown source of truth.

## When to use this example

- You want a live demonstration of the UiPath Integration Service for a non-UiPath SaaS target.
- You need the publish to run on an attended or unattended UiPath robot (e.g. post-merge, orchestrated from Automation Cloud).
- You are dogfooding: the fastest way to believe the agent can build production UiPath workflows is to watch it build the one that publishes its own README.

Use `ops/scripts/publish_confluence.py` instead if you just need the pages updated from a developer machine.

## One-time setup (Integration Service connection)

1. Open UiPath Automation Cloud → **Integration Service** → **Connections**.
2. Click **Add connection** → search for **Atlassian Confluence**.
3. Authenticate with the Cato Atlassian account. Name the connection `AtlassianConfluence-Cato`.
4. Note the connection's **Folder Path** — you will reference it from the workflow.

The connection is reused across projects. You only do this once per tenant.

## Prerequisites

- Installed per [docs/INSTALL.md](../../docs/INSTALL.md).
- Authenticated: `uipath auth --cloud --tenant <YourTenant>`.
- Integration Service Atlassian Confluence connection configured per above.
- Environment variables set (see `.env.example` in the repo root). For the coded workflow the relevant vars are the standard UiPath project vars (`UIPATH_ORCHESTRATOR_URL`, `UIPATH_TENANT_NAME`, `UIPATH_DEFAULT_FOLDER`) plus:
  - `CONFLUENCE_SPACE_KEY=RPA`
  - `CONFLUENCE_PARENT_PAGE_ID` (optional; Confluence page ID under which both pages are created)

For the Python publisher path (`ops/scripts/publish_confluence.py`), the extra vars are `UIPATH_ACCOUNT_NAME`, `UIPATH_IS_CONFLUENCE_CONNECTION_ID`, and either `UIPATH_PAT` or `UIPATH_CLIENT_ID` + `UIPATH_CLIENT_SECRET`. No Atlassian token is required on the developer machine — authentication flows through the Integration Service connection.

## Files

| File | Purpose |
|---|---|
| [`project.json`](project.json) | UiPath project manifest, pins `UiPath.IntegrationService.Activities`. |
| [`Main.xaml`](Main.xaml) | Thin XAML entry so `uip pack` works. Invokes the coded workflow. |
| [`PublishPage.cs`](PublishPage.cs) | Coded workflow: reads Markdown, converts to Confluence storage format, calls `ConnectorConnection.ExecuteAsync` for create/update. |

## Run

From the repo root:

```powershell
cd examples\04-publish-confluence
uip pack
uip rpa run-file Main.xaml --args "{\"OverviewPath\":\"..\\..\\docs\\wiki\\confluence-overview.md\",\"QuickstartPath\":\"..\\..\\docs\\wiki\\confluence-quickstart.md\"}"
```

On success the workflow logs the two Confluence page URLs and updates `docs/wiki/.confluence-ids.json` with their IDs so subsequent runs update in place instead of creating duplicates.

## How it works

The coded workflow follows the pattern in [skills/skills/uipath-rpa/references/coded/integration-service-guide.md](../../skills/skills/uipath-rpa/references/coded/integration-service-guide.md):

1. Build a `CodedConnectorConfiguration` from the typed `AtlassianConfluence` connection handle generated in `ISConnections.cs`.
2. For each Markdown file: read → convert to Confluence storage XHTML → look up existing page ID (if any) → `Operation.Create` or `Operation.Update` via `ConnectorConnection.ExecuteAsync`.
3. Write back the page IDs to `.confluence-ids.json`.

All metadata (object name, HTTP method, path template) is resolved up-front per the guide — no runtime `describe` lookups.

## Relevant skills

- `uipath-rpa` — coded workflow + Integration Service patterns.
- `uipath-automation` — project structure.
