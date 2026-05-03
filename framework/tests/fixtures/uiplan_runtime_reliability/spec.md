# InvoiceProcessor Runtime Reliability Spec

## Goal

Build a Studio-loadable InvoiceProcessor RPA fixture that proves UiPlan guidance can create
a working automation using scaffolded project structure, current dependencies, and pre-built
UiPath activities.

## Functional Requirements

- FR-001: Enumerate deterministic invoice text fixtures from `Data/Input`.
- FR-002: Extract invoice number, invoice date, and total amount from each fixture.
- FR-003: Validate missing invoice number, date format, and positive amount.
- FR-004: Write `Data/Output/invoice-report.csv` with one row per input fixture.
- FR-005: Write `Data/Output/smoke-result.json` with processed count and report name.

## Non-Functional Requirements

- NFR-001: Use `uip rpa create-project` scaffold evidence; do not hand-author `project.json`.
- NFR-002: Prefer pre-built UiPath activities. `InvokeCode` is prohibited for this fixture.
- NFR-003: Pass Studio designer validation, Studio build, local run, and analyzer gates.
- NFR-004: Record a structured tenant blocker when Orchestrator credentials are unavailable.
