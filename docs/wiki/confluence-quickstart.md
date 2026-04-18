# UiPath Claude Code - Quickstart for developers

Get running in ~5 minutes on a machine that already has Python 3.11+, Node.js 18+, UiPath Studio Desktop 26.2+, and AWS Bedrock access.

## Three commands

```
pip install -e ".[dev]"
aws sts get-caller-identity
uipath-claude chat
```

The first command installs the project in editable mode. The second confirms your AWS Bedrock credentials are valid. The third starts an interactive chat session.

## First prompts to try

- `Build me a UiPath project called QueueProcessor that reads the InvoiceQueue Orchestrator queue and logs each item.`
- `/bootstrap "Finance team gets PDF invoices in a shared mailbox, bot should extract and post to SAP"`
- `/skills` - list every skill the agent has loaded, with its origin.
- `/recall validator` - search recent sessions for anything involving the validator.

## Longer setup

UiPath CLI, Studio, submodules, Orchestrator auth, Cursor integration: see `docs/INSTALL.md` in the repo.

## Examples

Four runnable scenarios in the repo under `examples/`:

1. Chat-driven Orchestrator queue processor.
2. Full BA to SA to Dev to QA bootstrap from a one-paragraph brief.
3. The auto-fix loop catching a real validator error.
4. Dogfooding: a UiPath coded workflow that publishes these Confluence pages.

## Where to ask for help

- RPA CoE channel (Slack).
- Open an issue on the repo.
- Tag the project maintainers on the Azure DevOps wiki landing page.
