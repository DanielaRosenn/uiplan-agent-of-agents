# Example 02 — REFramework from a one-paragraph brief

**Goal:** produce a complete REFramework-based UiPath project — PDD, SDD, working code, QA report — from a single paragraph. This exercises the full BA → SA → Dev → QA pipeline with HITL approval points.

## Prerequisites

- Installed per [docs/INSTALL.md](../../docs/INSTALL.md).
- UiPath Studio Desktop 26.2+ installed and running (required for `--use-studio` validation).
- AWS Bedrock access working (`aws sts get-caller-identity`).

## Run

```bash
uipath-claude start-project "InvoicePostingBot"
```

When prompted for a brief, paste:

```
The Finance team receives invoices as PDF attachments in a shared mailbox.
The bot should download attachments from the last 24 hours, extract invoice
number, vendor, date, and amount using the UiPath Document Understanding
package, post each invoice as a draft journal entry in SAP via the UiPath
SAP connector, and send a summary email to finance-ops@cato. Reprocess on
transient errors; escalate invoices over $50,000 to a human queue.
```

## What happens

1. **BA agent** writes the PDD (`generated/chat/<session>/docs/PDD.md`). You approve or adjust.
2. **SA agent** writes the SDD (`generated/chat/<session>/docs/SDD.md`). You approve or adjust.
3. **Developer agent** scaffolds an REFramework project, implements the workflows, runs `validate_file` on each, and enters the auto-fix loop on any validator errors.
4. **QA agent** runs `run_workflow` against sample data and writes a QA report (`generated/chat/<session>/docs/QA_Report.md`).

Approved plans for each step are saved as `.plan.md` files in the session directory.

## Expected output

```
generated/chat/<session-id>/
  docs/
    PDD.md
    SDD.md
    QA_Report.md
  InvoicePostingBot/
    project.json
    Main.xaml
    Framework/                # REFramework states
    Data/
    Tests/
```

## Relevant skills

- `uipath-reframework` — REFramework patterns.
- `uipath-automation` — XAML and activity reference.
- `uipath-code-reviewer` — QA gate.
- `uipath-diagnostics` — error interpretation.
