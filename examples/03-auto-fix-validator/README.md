# Example 03 — The auto-fix loop

**Goal:** watch `validate_and_fix_loop` catch and resolve a real UiPath Workflow Analyzer error. This is the flagship example — the behaviour the README's "A real example" section is showing.

## Prerequisites

- Installed per [docs/INSTALL.md](../../docs/INSTALL.md).
- UiPath Studio Desktop 26.2+ running.
- Agentic mode on:

```powershell
$env:UIPATH_AGENTIC_MODE = "1"
$env:UIPATH_DEBUG_AGENT = "1"
```

## Run

```bash
uipath-claude chat
```

Prompt:

```
Build me an InvoiceProcessor workflow that reads Sample.xlsx and logs each invoice id.
```

A sample `Sample.xlsx` is provided at [Sample.xlsx](Sample.xlsx) (or generate one with two columns: `InvoiceId`, `Amount`).

## Expected transcript

The annotated transcript below is a recorded session. Your output will match step-for-step if the skill registry is unchanged.

```text
> Build me an InvoiceProcessor workflow that reads Sample.xlsx and logs each invoice id.

[Step 1/25] ensure_project_structure(name="InvoiceProcessor")
   -> created InvoiceProcessor/project.json, Main.xaml
[Step 2/25] install_package("UiPath.Excel.Activities")
   -> ok
[Step 3/25] write_file("InvoiceProcessor/Main.xaml", <first attempt>)
[Step 4/25] validate_file("InvoiceProcessor/Main.xaml")
   -> ERRORS (2):
      - UiPath.Excel.Activities.ExcelReadRange: 'Range' is required
      - Variable 'dt_Invoices' used before assignment
[Step 5/25] validate_and_fix_loop
   -> interpreting errors, rewriting XAML...
[Step 6/25] write_file("InvoiceProcessor/Main.xaml", <revised>)
[Step 7/25] validate_file("InvoiceProcessor/Main.xaml")
   -> OK (0 errors, 0 warnings)
[Step 8/25] run_workflow("InvoiceProcessor")
   -> OK: processed 14 invoices in 1.2s

Done. Generated at generated/chat/<session-id>/InvoiceProcessor/.
```

## What to notice

- **Step 4** is a real validator error from `uip rpa --use-studio`, not a fabricated one. The agent did not pre-check the activity's required properties, it let the validator fail first.
- **Step 5** is the loop: it reads the validator output, diffs the XAML, and writes a fix.
- **Step 8** is the runtime gate. A workflow that passes static validation but fails at runtime is not "done" in this system.

## Relevant skills

- `uipath-diagnostics` — validator error interpretation.
- `uipath-automation` — activity property reference.
