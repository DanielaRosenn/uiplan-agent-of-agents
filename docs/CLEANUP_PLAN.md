# Repository Cleanup Plan

## Objectives

- Reduce root-folder noise.
- Keep product code and docs discoverable.
- Preserve historical artifacts without deleting potentially useful files.

## Rules

- Product code stays in `uipath_claude/`, `tests/`, `skills/`, `templates/`, `docs/`.
- One-off reports and generated evaluation outputs move under `archive/`.
- Utility scripts not part of runtime move under `scripts/maintenance/`.
- Local runtime artifacts stay untracked via `.gitignore`.

## Applied Cleanup

### Archived reports

Moved to `archive/reports/2026-04-09/`:
- `COMPREHENSIVE_CODE_REVIEW_96.5_PERCENT_20260409_104557.xlsx`
- `COMPREHENSIVE_CODE_REVIEW_96.5_PERCENT_20260409_104611.xlsx`
- `COMPREHENSIVE_CODE_REVIEW_REPORT.xlsx`
- `FINAL_COMPREHENSIVE_EVALUATION_SUMMARY.md`
- `FINAL_QUALITY_REPORT_96.5_PERCENT.md`
- `PROJECT_COMPLETE_FINAL_REPORT.md`
- `PROJECT_FILE_INVENTORY.md`
- `RUNTIME_DEMONSTRATION_RESULTS.md`
- `SPRINT1_COMPLETION_REPORT.md`
- `SPRINT1_COMPREHENSIVE_EVALUATION_REPORT.xlsx`
- `USER_GUIDE.md`

### Rehomed maintenance scripts

Moved to `scripts/maintenance/`:
- `create_comprehensive_evaluation.py`
- `create_comprehensive_review_excel.py`
- `create_evaluation_report.py`
- `demo_run.py`

### Archived legacy docs

Moved to `archive/docs/legacy/`:
- `docs/API_DOCUMENTATION.md`
- `docs/REFACTORING_PLAN.md`

### Removed local noise

Deleted local artifacts:
- `.coverage`
- `coverage.json`
- `htmlcov/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.mypy_cache/`

### Ignore rules updated

Added to `.gitignore`:
- `.venv/`
- `coverage.json`

## Next optional cleanup

- Add `archive/README.md` with retention policy.
- Add `scripts/maintenance/README.md` with script purpose and usage.
- Review duplicate quickstart/implementation docs and merge if desired.

## L3 verification gates (automation)

Run from repo root (after `pip install -e .`):

- `pytest tests/unit/skills -v`
- `pytest tests/unit/commands -v`
- `pytest tests/unit/tools/uipath -v`
- `pytest tests/unit/query/test_router.py -v`
- `pytest tests/integration/test_chat_flow.py tests/integration/test_bootstrap_flow.py -v`
- `pytest tests/ -v`
- `python scripts/maintenance/smoke_cli.py`

Bootstrap output directories: `docs/pdd/`, `docs/sdd/`, `docs/qa/`, and `generated/` (ignored by git) under the working directory.
