# Library CLI Evaluations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add six `Library` category cases to the CLI evaluation harness so library read tools and `propose_library_update` are regression-tested.

**Architecture:** Extend `CATEGORY_TIMEOUTS` in `docs/evaluations/run_evaluations.py`, set `UIPATH_CLAUDE_LIBRARY_PROPOSALS` to a temp directory when `category == "Library"`, append cases to `docs/evaluations/test_cases.json`, document in `HOW_TO_RUN_TESTS.md`.

**Tech Stack:** Existing `run_evaluations.py` harness, JSON test cases, PowerShell.

---

### Task 1: Runner timeout and isolated proposals dir

**Files:**
- Modify: `docs/evaluations/run_evaluations.py`
- Modify: `docs/evaluations/HOW_TO_RUN_TESTS.md`

- [ ] Add `'Library': 60` to `CATEGORY_TIMEOUTS`.
- [ ] In `CLITestRunner.run_test`, if `category.strip() == 'Library'`, set `env['UIPATH_CLAUDE_LIBRARY_PROPOSALS']` to `tempfile.mkdtemp(prefix='uipath-lib-eval-proposals-')`.
- [ ] Add a `Library` row to the category timeout table in `HOW_TO_RUN_TESTS.md`.

---

### Task 2: Append `LIB-001` … `LIB-006` to `test_cases.json`

**Files:**
- Modify: `docs/evaluations/test_cases.json`

- [ ] Append six objects before the closing `]` of `test_cases`, each with `"category": "Library"`, `"expected.technical.mode": "direct_response"`, `tool_calls_required` as specified in the execution plan table, `no_file_creation` and `crash_not_allowed` true, and conceptual checks per case (empty `conceptual` for `LIB-006`).

---

### Task 3: Baseline run and commit results

**Files:**
- Create under: `docs/evaluations/results/run_20260417_library/`

- [ ] From repo root: `python docs/evaluations/run_evaluations.py --category Library`
- [ ] Expect six passing runs; copy or write per-test JSON into `docs/evaluations/results/run_20260417_library/`.
- [ ] Commit results if CI policy allows committed baselines.
