# Archive

This folder stores historical or generated artifacts that are not part of the runtime product.

## Policy

- Keep product code in root modules (`uipath_claude`, `tests`, `docs`).
- Move one-off reports, generated spreadsheets, and legacy snapshots to `archive/`.
- Do not import or execute code from this folder in runtime paths.

## Structure

- `reports/` - generated assessment/review outputs
- `docs/legacy/` - old docs retained for traceability

