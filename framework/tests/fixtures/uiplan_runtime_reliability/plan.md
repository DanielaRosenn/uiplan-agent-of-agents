# InvoiceProcessor Runtime Reliability Plan

## Scaffold

- Source: `uip rpa create-project`
- Template: `BlankTemplate`
- Expression language: `CSharp`
- Target framework: `Windows`
- Project path: `framework/tests/fixtures/uiplan_runtime_reliability/InvoiceProcessor`
- Evidence: `evidence/scaffold.json`

## Activity Inventory

- `Log Message`
  - Package: `UiPath.System.Activities` `26.2.4`
  - Evidence: `uip rpa find-activities --query "Log Message"`
  - Binding rule: literal messages use explicit `CSharpValue` child elements.
- `Create Directory`
  - Package: `UiPath.System.Activities` `26.2.4`
  - Evidence: `uip rpa find-activities --query "Create Folder"`
  - Default XAML evidence: `evidence/default-create-directory.json`
- `For Each`
  - Package: `UiPath.System.Activities` `26.2.4`
  - Evidence: activity docs for `ForEach`.
  - Required scope: body sequence with matching `x:String` type arguments.
- `Read Text File`
  - Package: `UiPath.System.Activities` `26.2.4`
  - Evidence: `uip rpa find-activities --query "Read Text File"`
  - Default XAML evidence: `evidence/default-read-text-file.json`
- `Assign`
  - Package: built-in workflow activity.
  - Evidence: C# expression bindings use `CSharpReference` and `CSharpValue`.
- `Write Text File`
  - Package: `UiPath.System.Activities` `26.2.4`
  - Evidence: `uip rpa find-activities --query "Write Text File"`
  - Default XAML evidence: `evidence/default-write-text-file.json`

## Local Evidence

- Studio designer validation: `out/get-errors.json`
- Studio build: `out/build.json`
- Analyzer result: `out/analyze.json`
- Local run: `out/local-run.json`
- Output report: `InvoiceProcessor/Data/Output/invoice-report.csv`
- Smoke result: `InvoiceProcessor/Data/Output/smoke-result.json`

## Tenant Evidence

Tenant smoke is intentionally blocked in this fixture unless non-Production Orchestrator
credentials and folder configuration are present in the environment. The blocker is recorded
in `out/tenant-blocker.json`.
