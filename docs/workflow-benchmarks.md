# Workflow Benchmark Suite

This repository includes a repeatable benchmark suite focused on **real UiPath CLI validation** (not mocked-only checks).

## Goals

- Catch regressions where generated workflows "pass" local parsing but fail in Studio.
- Keep a stable set of baseline workflows that must validate after every improvement.
- Include a Maestro Flow benchmark path for Flow project validation.

## Test Architecture

The benchmark suite consists of two complementary test systems:

### 1. Pytest Integration Tests (`tests/integration/`)

Python-based tests that validate the agent's workflow generation capabilities:

| Test File | Purpose | Requires CLI |
|-----------|---------|--------------|
| `test_workflow_benchmarks.py` | Template validation with real `uip` CLI | Yes |
| `test_mail_workflow_generation.py` | Mail activity correctness guards | No |
| `test_chat_skill_picking_outputs.py` | Skill selection and file materialization | No |
| `test_agent_workflow_generation.py` | Full agent flow with LLM (optional) | Optional |
| `test_chat_flow.py` | Chat session flow tests | No |
| `test_chat_materialize.py` | File block parsing and writing | No |
| `test_bootstrap_flow.py` | Bootstrap flow (BA/SA/Dev/QA) | Optional |

### 2. Coder-Eval Skill Tests (`skills/tests/`)

YAML-based tests that verify AI agents correctly use skills:

| Skill | Test Directory | Status |
|-------|----------------|--------|
| `uipath-maestro-flow` | `skills/tests/tasks/uipath-maestro-flow/` | Implemented |
| `uipath-rpa` | `skills/tests/tasks/uipath-rpa/` | **TODO** |

## Benchmarks Included

### Template Validation Benchmarks

| Benchmark | Template | Validation Command | Expected Result |
|-----------|----------|-------------------|-----------------|
| Dispatcher | `templates/dispatcher` | `uip rpa get-errors` | No diagnostics |
| Long-running | `templates/long-running` | `uip rpa get-errors` | No diagnostics |
| Performer | `templates/performer` | `uip rpa get-errors` | No diagnostics |

### Maestro Flow Benchmark

Creates a solution and Flow project, then validates with `uip flow validate`.

### Mail Workflow Guards

Validates that generated mail workflows:
- Use `System.Net.Mail.MailMessage` (NOT `ui:OutlookMailItem`)
- Use `ui:GetOutlookMailMessages` (NOT legacy scope chains)
- Detect and warn on hallucinated activities

## Running Benchmarks

### Pytest Benchmarks

```powershell
# Run all integration tests (mocked, no CLI required)
pytest tests/integration/ -v -m integration

# Run real CLI benchmark tests (requires uip CLI)
$env:UIPATH_RUN_BENCHMARKS="1"
pytest tests/integration/test_workflow_benchmarks.py -v

# Run mail generation guard tests
pytest tests/integration/test_mail_workflow_generation.py -v

# Run skill picking tests
pytest tests/integration/test_chat_skill_picking_outputs.py -v
```

### Coder-Eval Skill Tests

```bash
cd skills/tests

# Install coder-eval (one-time setup)
make install

# Run all smoke tests
make smoke

# Run all tests for a specific skill
make test-uipath-maestro-flow

# Run a single task
SKILLS_REPO_PATH=$(cd .. && pwd) \
  .venv/bin/coder-eval run tasks/uipath-maestro-flow/init_validate.yaml \
  -e experiments/default.yaml
```

## Expected Behavior

| Test Category | Expected Outcome |
|---------------|------------------|
| Template validation | `No diagnostics found.` from `uip rpa get-errors` |
| Maestro Flow | Creates and validates `.flow` project successfully |
| Mail workflows | Uses correct `snm:MailMessage` types, no legacy activities |
| Hallucinated activities | Produces warnings during materialization |
| Skill picking | Selects `uipath-rpa` for workflow intents |

## Debugging Checklist

1. **Validation failures**: Run `uip rpa get-errors --project-dir <project> --output json`
2. **Activity not found**: Run `uip rpa find-activities --query <ActivityName> --output json`
3. **Generation looks valid but Studio fails**: Inspect `validate_generated_project()` output
4. **Flow issues**: Run `uip flow validate <flow-file> --output json`
5. **Skill not selected**: Check `_debug_skill_selection()` output with `UIPATH_CHAT_DEBUG_SKILLS=1`

## Adding New Benchmarks

### Adding Pytest Benchmarks

1. Create test in `tests/integration/test_<category>.py`
2. Mark with `@pytest.mark.integration`
3. For CLI-dependent tests, check `UIPATH_RUN_BENCHMARKS` env var
4. Update this document

### Adding Coder-Eval Tests

1. Create YAML task in `skills/tests/tasks/<skill-name>/`
2. Follow the task structure in `skills/tests/README.md`
3. Tag appropriately: `smoke`, `integration`, or `e2e`
4. Run with `make test-<skill-name>`
