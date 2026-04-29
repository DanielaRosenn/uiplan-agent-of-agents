# Subagent routing evaluation report

**Date:** 2026-04-29  
**Commit:** `08fad47`  
**Scope:** CLI harness routing fields, `Subagent Routing` seed cases, ADD/TDD-as-document-type model, docs + manual rubric, routing-risk fixes.

## Verification run

| Command | Result |
|---------|--------|
| `python -m json.tool docs/evaluations/test_cases.json` | OK (valid JSON) |
| `uv run pytest framework/tests/test_evaluation_output_parser.py framework/tests/unit/query/test_persona_router.py framework/tests/mcp_tests/test_answer_tools.py framework/tests/mcp_tests/test_intent_tools.py -q` | **54 passed** |

## Full CLI category run (`Subagent Routing`)

**Not executed** in this session: seed cases are LLM-backed and require Bedrock/AWS (or equivalent) plus time (~180s cap per case). The deterministic parser/router layer is verified; run live cases locally when ready:

```powershell
cd <REPO_ROOT>
$env:UIPATH_SKIP_AUTH_CHECK = "1"
uv run python docs/evaluations/run_evaluations.py --category "Subagent Routing"
# or smoke one case:
uv run python docs/evaluations/run_evaluations.py --test SUB-DISC-001
```

Record pass/fail counts from `docs/evaluations/results/run_summary.json` and `TRIAGE.md` after a live run.

## Cohort coverage (seed IDs)

| Prefix | Cases | Notes |
|--------|-------|------|
| SUB-DISC | 001–002 | Discovery / conventions |
| SUB-DIAG | 001–005 | Triage → presenter-style prompts |
| SUB-PER | BA, SA, Dev, QA | Role-flavored prompts |
| SUB-DOC | ADD, TDD | Document outlines; read-only gates plus non-blocking `document_type_required` checks |
| SUB-MCP | 001–004 | Routing/intent/MCP *concepts* via chat (not isolated MCP wire protocol) |
| SUB-SAFE | 001–003 | Forbidden phrases on assistant response + stderr (not the user's unsafe prompt text) |

## Academy grounding

Personas align with UiPath Academy Automation Career Paths (Business Analyst, Solution Architect, Developer, Test Automation Engineer). Document outputs (ADD/TDD) are **not** personas — see `docs/evaluations/SUBAGENT_PERSONA_MATRIX.md`.

## Risk fixes applied

1. **Document-output observability:** ADD/TDD persona runs now have a structured `[DOCUMENT_TYPE: ADD|TDD]` marker when the agentic executor receives `document_type` / `selected_document_type`. The evaluation parser records `document_types`, and `TechnicalEvaluator` supports `document_type_required` / `document_type_forbidden`.
2. **Safety false positives:** `safety_forbidden_phrases` now checks `safety_text` (assistant response + stderr) before falling back to `combined_text`, so unsafe examples embedded in the user prompt do not fail unless the assistant echoes/leaks them.
3. **Case hardening:** SUB-DOC cases now include non-blocking document-type requirements, and safety checks remain deterministic without relying on full-transcript matching.

## Residual risks / follow-ups

1. **Live chat route coverage:** CLI `Subagent Routing` cases still need a live LLM run to establish pass/fail rates; deterministic parser/router behavior is covered.
2. **Conceptual checks:** Substrings in `test_cases.json` can still flake if the model paraphrases; tighten only after stable transcripts.
3. **Skill marker coverage:** Persona Q&A via the agentic executor emits `[SKILL: …]`; direct simple-answer chat paths may not. Treat missing markers in live results as an observability gap to triage, not a reason to fake markers.

## Files touched (implementation summary)

- Harness: `docs/evaluations/run_evaluations.py` — `TechnicalEvaluator` routing checks, `document_types`, response-scoped `safety_text`, triage columns.
- Cases: `docs/evaluations/test_cases.json` — `Subagent Routing` seeds (`skip_in_default_batch`: true).
- Router/MCP: `framework/uipath_claude/query/persona_selection.py`, `persona_router.py`, MCP tools/tests — BA/SA/Developer/QA only; ADD/TDD via SA + `document_type`.
- Runtime markers: `framework/uipath_claude/rendering/progress.py`, `framework/uipath_claude/query/agentic_executor.py` — emit `[DOCUMENT_TYPE: ADD|TDD]` when document output type is selected.
- Docs: `docs/evaluations/README.md`, `HOW_TO_RUN_TESTS.md`, `MANUAL_EVAL_AND_QA.md`, `SUBAGENT_PERSONA_MATRIX.md`.
- Unit tests: `framework/tests/test_evaluation_output_parser.py`, `framework/tests/unit/query/test_persona_router.py`, MCP tests.
