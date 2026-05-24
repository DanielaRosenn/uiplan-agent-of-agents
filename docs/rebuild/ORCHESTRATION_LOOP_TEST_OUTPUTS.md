# Orchestration Loop Test Outputs

## Unit test run
- Command:
  - `uv run pytest agents/shared/tests/test_contracts.py agents/builder-orchestrator/tests/test_orchestrator.py -q`
- Result:
  - `12 passed`

## Loop-specific coverage
- `test_build_loop_escalates_when_budget_exhausted` validates build-cap escalation.
- `test_handoff_contains_execution_evidence` validates runtime evidence payload.
- `test_run_writes_handoff_file_structure` validates generated run events path.

## End-to-end local run
- Command:
  - `python examples/agent-of-agents-e2e/run_local.py`
- Result:
  - `run_id=enterpriseincidentagentbuilder-20260524124819`
  - `status=completed`
  - `handoff_file=agents/builder-orchestrator/out/enterpriseincidentagentbuilder-20260524124819/handoff.json`
