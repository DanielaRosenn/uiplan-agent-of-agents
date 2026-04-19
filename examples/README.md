# Examples

Runnable scenarios for UiPath Claude Code. Each folder is self-contained and links back to the relevant skills.

| # | Example | What it demonstrates |
|---|---|---|
| 01 | [orchestrator-queue-processor](01-orchestrator-queue-processor/) | Chat-driven scaffold + validate of a simple Orchestrator queue processor. |
| 02 | [reframework-from-brief](02-reframework-from-brief/) | Full BA → SA → Dev → QA bootstrap from a one-paragraph brief. |
| 03 | [auto-fix-validator](03-auto-fix-validator/) | The auto-fix loop resolving a real UiPath validator error. |
| 04 | [publish-confluence](04-publish-confluence/) | Dogfooding: a UiPath coded workflow publishes this repo's docs to Confluence via the Integration Service. |
| 05 | [InvoiceQueueProcessor](InvoiceQueueProcessor/) | Unattended queue performer, **activities-first XAML** build: `WaitQueueItem` -> validation (one `Invoke Code`) -> `ExecuteNonQuery` insert into SQL Server -> `SetTransactionStatus` Successful / Failed (Business or Application). No coded workflow. |

Start with example 01 if you are new. Run example 04 only after configuring the Atlassian Confluence Integration Service connection in UiPath Automation Cloud.
