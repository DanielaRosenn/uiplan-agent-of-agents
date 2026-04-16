# CLI evaluation harness hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the two-stage CLI evaluation runner (`docs/evaluations/run_evaluations.py`) and `test_cases.json` so deployment and build+deploy scenarios pass when the agent legitimately uses different but equivalent tools, without weakening checks that still catch real regressions.

**Architecture:** Extend `TechnicalEvaluator` with a small OR-group for required tools (`tool_calls_required_any_of`), keep existing `tool_calls_required` (AND) and `tool_calls_optional` unchanged. Add focused pytest coverage for `OutputParser` / mode / tool evaluation loaded via `importlib` from `docs/evaluations/run_evaluations.py`. Update `DEPLOY-001` expectations and document multi-test CLI usage in `HOW_TO_RUN_TESTS.md`.

**Tech stack:** Python 3.11+, pytest, existing repo layout (`docs/evaluations/`, `tests/`).

---

## File map

| File | Responsibility |
|------|----------------|
| `docs/evaluations/run_evaluations.py` | Parsing, `TechnicalEvaluator`, `ConceptualEvaluator`, CLI runner |
| `docs/evaluations/test_cases.json` | Per-test `expected.technical` / `expected.conceptual` |
| `docs/evaluations/HOW_TO_RUN_TESTS.md` | How to run subsets, timeouts, flags |
| `tests/test_evaluation_output_parser.py` | New: unit tests for parser and tool OR-group |

---

### Task 1: Add `tool_calls_required_any_of` to `TechnicalEvaluator`

**Files:**

- Modify: `docs/evaluations/run_evaluations.py` (method `_check_tool_calls` on class `TechnicalEvaluator`, immediately after the block that processes `tool_calls_required`)

**Behavior:** If `expected["technical"]` contains key `tool_calls_required_any_of` with a non-empty list of tool name strings, pass when **at least one** of those names appears in `self.output["tool_calls"]` (same source as today: `[TOOL_CALL: name]` markers in stdout). Fail with message `Missing required tool (need any of): [...]` when none match. If the list is empty or key absent, do nothing (backward compatible).

- [x] **Step 1: Edit `_check_tool_calls`**

Insert after the existing `for tool in required:` loop (after line that appends failures for missing required tools), before the `optional = ...` block:

```python
        any_of = self.expected.get("tool_calls_required_any_of") or []
        if any_of:
            actual_tools = self.output.get("tool_calls", [])
            if any(tool in actual_tools for tool in any_of):
                self.results["passed"].append(
                    f"Required tool group satisfied: one of {any_of!r}"
                )
            else:
                self.results["failed"].append(
                    f"Missing required tool (need any of): {any_of}"
                )
```

- [x] **Step 2: Run a quick smoke import**

Run:

```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
python -c "import importlib.util; from pathlib import Path; p=Path('docs/evaluations/run_evaluations.py'); s=importlib.util.spec_from_file_location('re', p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); e=m.TechnicalEvaluator({'tool_calls':['read_file'],'mode':'planning_then_execution','crashed':False,'files_written':[],'errors':[]},{'tool_calls_required_any_of':['ensure_project_structure','read_file']}); r=e.evaluate(); assert r['passed'], r"
```

Expected: no traceback (assert passes).

- [x] **Step 3: Commit** (merged into `feat(eval): tool_calls_required_any_of, DEPLOY-001, parser tests, docs`)

---

### Task 2: Point `DEPLOY-001` at the OR-group and drop brittle single-tool requirement

**Files:**

- Modify: `docs/evaluations/test_cases.json` (object with `"test_id": "DEPLOY-001"`, path under `test_cases` array)

- [x] **Step 1: Replace `tool_calls_required` with `tool_calls_required_any_of`**

In the `DEPLOY-001` entry, inside `expected.technical`, remove:

```json
"tool_calls_required": ["ensure_project_structure"],
```

Add:

```json
"tool_calls_required_any_of": [
  "ensure_project_structure",
  "read_project_json",
  "deploy_to_orchestrator"
],
```

Leave `tool_calls_optional` as-is (duplicate names in optional vs any_of is harmless: optional loop only adds pass lines when present).

- [ ] **Step 2: Run only this test** (optional; slow LLM — run locally when needed)

```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
python -u docs/evaluations/run_evaluations.py --test DEPLOY-001
```

Expected: `Technical: PASS` in console (conceptual may still show `PASS (0/0)` if branching keys are not implemented; that is acceptable for this task).

- [x] **Step 3: Commit** (merged into single harness commit)

---

### Task 3: Pytest coverage for parser and OR-group

**Files:**

- Create: `tests/test_evaluation_output_parser.py`

- [x] **Step 1: Create the test file with full content**

```python
"""Unit tests for docs/evaluations/run_evaluations.py parser and technical OR-tools."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load_eval_module():
    path = _ROOT / "docs" / "evaluations" / "run_evaluations.py"
    spec = importlib.util.spec_from_file_location("eval_run", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ev():
    return _load_eval_module()


def test_detect_mode_exit(ev):
    stdout = (
        "Chat session started.\n\n"
        "You: Goodbye!\n"
    )
    assert ev.OutputParser.detect_mode(stdout) == "exit"


def test_mode_compatible_execution_vs_pte(ev):
    assert ev.TechnicalEvaluator._mode_compatible("execution", "planning_then_execution")


def test_extract_assistant_response_prefers_plan_over_short_preview(ev):
    stdout = (
        "[EXECUTING]\n"
        "┌──────────────────────────── Implementation Plan ─────────────────────────────┐\n"
        "│ ForEachRow and Excel row processing                                           │\n"
        "└──────────────────────────────────────────────────────────────────────────────┘\n"
        "  Preview: Short summary without the word Excel.\n"
        "Agent finished after 1 iteration(s)\n"
        "You: Goodbye!\n"
    )
    text = ev.OutputParser.extract_assistant_response(stdout)
    assert "foreachrow" in text.lower() or "excel" in text.lower()


def test_tool_calls_required_any_of_passes_when_one_present(ev):
    evl = ev.TechnicalEvaluator(
        {
            "tool_calls": ["read_project_json", "write_file"],
            "mode": "planning_then_execution",
            "crashed": False,
            "files_written": [],
            "errors": [],
        },
        {
            "tool_calls_required_any_of": [
                "ensure_project_structure",
                "read_project_json",
            ],
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["passed"] is True


def test_tool_calls_required_any_of_fails_when_none_present(ev):
    evl = ev.TechnicalEvaluator(
        {
            "tool_calls": ["list_directory"],
            "mode": "planning_then_execution",
            "crashed": False,
            "files_written": [],
            "errors": [],
        },
        {
            "tool_calls_required_any_of": ["deploy_to_orchestrator", "read_project_json"],
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["passed"] is False
    assert any("need any of" in f for f in out["details"]["failed"])
```

- [x] **Step 2: Run pytest on this file**

```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
python -m pytest tests/test_evaluation_output_parser.py -v
```

Expected: `5 passed`.

- [x] **Step 3: Commit** (merged into single harness commit)

---

### Task 4: Document multiple `--test` flags and refresh timeout hints

**Files:**

- Modify: `docs/evaluations/HOW_TO_RUN_TESTS.md` (section “Options”, after the single-test example)

- [x] **Step 1: Insert documentation block**

After the block that shows `python docs/evaluations/run_evaluations.py --test QA-001`, add:

````markdown
# Several tests by id (repeat --test)
python docs/evaluations/run_evaluations.py --test QA-001 --test QA-002 --test DEPLOY-001
````

In the same section, update the comment on line that says `QA=60s` to reflect current defaults if still wrong, for example: `Question` category is **180s** unless `--timeout` overrides (grep `CATEGORY_TIMEOUTS` in `run_evaluations.py` and mirror the values in one sentence).

- [x] **Step 2: Commit** (merged into single harness commit)

---

### Task 5 (optional): Implement or strip unused `conceptual.on_success` keys for `DEPLOY-001`

**Files:**

- Modify: `docs/evaluations/run_evaluations.py` (`ConceptualEvaluator.evaluate` and new small helper), **or** modify: `docs/evaluations/test_cases.json` (remove `on_success` / `on_auth_error` if you choose doc-only cleanup)

**Decision branch:**

- **Option A (implement):** If `deploy_to_orchestrator` in `parsed["tool_calls"]`, merge `expected["conceptual"].get("on_success", {})` into a temporary dict and run the same checks as flat conceptual (at least `response_must_contain_any`). Else merge `on_auth_error`. This is more code and needs golden stdout fixtures; only pick if product owners want enforced branching.

- **Option B (strip, recommended for YAGNI):** Remove `on_success`, `on_auth_error`, `expected_response_pattern_success`, `expected_response_pattern_error` from `DEPLOY-001` only, leaving a single flat `conceptual` block later when you add real phrases, **or** leave keys as documentation comments in `HOW_TO_RUN_TESTS.md` instead of JSON.

- [x] **Step 1:** Chose **Option B** (strip non-enforced conceptual keys).

- [x] **Step 2:** `DEPLOY-001` now has `"conceptual": {}`.

- [x] **Step 3:** Same commit as harness work.

---

### Task 6: Re-run failed-only slice after merge

**Files:** none (verification only)

- [ ] **Step 1:** From repo root, run the last failing list (adjust IDs from latest `docs/evaluations/results/TRIAGE.md`):

```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
python -u docs/evaluations/run_evaluations.py --test DEPLOY-001 --test BUILD-DEPLOY-001 --test BUILD-DEPLOY-002
```

Expected: `SUMMARY` shows all `PASS` for the IDs you include, or documented product failures filed as separate issues.

- [ ] **Step 2:** Attach `docs/evaluations/results/run_summary.json` to the PR or ticket.

---

## Self-review

1. **Spec coverage:** OR-tool requirement, DEPLOY-001 stability, docs for `--test`, regression tests for parser, optional conceptual branching — all mapped. Remaining gap: **“Unknown tool” in logs** is a product/registry issue in `uipath_claude`; add a separate plan if you want a full tool-map audit (out of scope here).

2. **Placeholder scan:** No `TBD` / empty steps; optional Task 5 forces an explicit A/B choice.

3. **Type consistency:** `tool_calls_required_any_of` is always a JSON array of strings, matching `tool_calls` entries from the same marker format as `tool_calls_required`.

---

**Plan complete and saved to** `docs/superpowers/plans/2026-04-16-cli-evaluation-hardening.md`.

**Execution options:**

1. **Subagent-driven (recommended)** — Fresh subagent per task, review between tasks (`superpowers:subagent-driven-development`).

2. **Inline execution** — Run tasks in this session with checkpoints (`superpowers:executing-plans`).

Which approach do you want?
