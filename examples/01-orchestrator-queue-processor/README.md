# Example 01 — Orchestrator queue processor

**Goal:** scaffold a minimal UiPath project that pulls queue items from Orchestrator, processes each, and marks them complete. End-to-end runtime is ~2 minutes.

## Prerequisites

- Installed per [docs/INSTALL.md](../../docs/INSTALL.md).
- Authenticated: `uipath auth --cloud --tenant <YourTenant>`.
- An Orchestrator queue named `InvoiceQueue` (empty is fine) in the folder configured in `.env` (`UIPATH_DEFAULT_FOLDER`).

## Run

```bash
uipath-claude chat
```

Prompt:

```
Build me a UiPath project called QueueProcessor that:
- connects to the InvoiceQueue Orchestrator queue
- processes each queue item (log the SpecificContent)
- marks items as Successful
Validate it and run it.
```

## Expected output

Generated project at `generated/chat/<session-id>/QueueProcessor/`:

```
QueueProcessor/
  project.json        # deps: UiPath.System.Activities, UiPath.Orchestrator.Activities
  Main.xaml           # GetTransactionItem -> Log -> SetTransactionStatus
```

Validator output (what the agent sees after `validate_file`):

```
OK (0 errors, 0 warnings)
```

Runtime output (from `run_workflow`):

```
OK: processed 0 transactions from InvoiceQueue (queue empty)
```

Drop a test item into `InvoiceQueue` from the Orchestrator UI and rerun to see the loop execute.

## Relevant skills

- `uipath-automation` — base XAML generation.
- `uipath-orchestrator` — queue activity patterns.
- `uipath-diagnostics` — if validation fails and the auto-fix loop kicks in.
