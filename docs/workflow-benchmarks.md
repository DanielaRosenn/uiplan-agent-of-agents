# Workflow Benchmark Suite

This repository includes a repeatable benchmark suite focused on **real UiPath CLI validation** and **agentic execution**.

## The Canonical Evaluation Method

We have consolidated our evaluation framework into **ONE single evaluation script** that is always used to measure agent performance. This ensures consistency and reliability across all tests.

### `run_evals.py`

This script is the single entry point for running the comprehensive evaluation suite (57 test cases, including 54 from the DeepAgent Eval Suite).

It uses the unified `agent_benchmark_evaluator` which combines:
1. **Outcome Scoring**: Checks if the expected files were created, packages installed, and if static validation passed.
2. **Trajectory Scoring**: Checks if the agent used the correct sequence of tools (e.g., `ensure_project_structure` -> `install_package` -> `write_file` -> `validate_file` -> `run_workflow`).

The benchmark agent instructions live in `uipath_claude/evaluation/eval_skill_prompt.py` (`EVAL_AGENT_SKILL_PROMPT`). Each run sets `UIPATH_CHAT_SESSION_ID` so tools write under the same session folder as `project_context`. **Static validation in scores** uses `validation_passed`: true when `tool_failure_count == 0` and the executor reported no fatal `error` (not merely “the LLM finished the loop”).

### Running Evaluations

To run the full evaluation suite:

```powershell
# Run the entire suite (all 57 examples)
python run_evals.py

# Run a specific number of examples
python run_evals.py --max-examples 5

# Filter by category (e.g., "email", "excel", "web")
python run_evals.py --category "email"

# Output to a specific file
python run_evals.py --output "my_results.json"
```

The script will output a detailed `evaluation_results.json` file containing the scores, pass rates, and detailed trajectory matching for the agent's performance.

## Test Architecture

While `run_evals.py` is the canonical way to evaluate the agent end-to-end, the repository also contains complementary test systems for CI/CD and skill-specific testing:

### 1. Pytest Integration Tests (`tests/integration/`)

Python-based tests that validate the agent's workflow generation capabilities without running the full LLM loop:

| Test File | Purpose | Requires CLI |
|-----------|---------|--------------|
| `test_workflow_benchmarks.py` | Template validation with real `uip` CLI | Yes |
| `test_mail_workflow_generation.py` | Mail activity correctness guards | No |
| `test_chat_skill_picking_outputs.py` | Skill selection and file materialization | No |
| `test_chat_flow.py` | Chat session flow tests | No |
| `test_chat_materialize.py` | File block parsing and writing | No |

### 2. Coder-Eval Skill Tests (`skills/tests/`)

YAML-based tests that verify AI agents correctly use specific skills:

| Skill | Test Directory | Status |
|-------|----------------|--------|
| `uipath-maestro-flow` | `skills/tests/tasks/uipath-maestro-flow/` | Implemented |
| `uipath-rpa` | `skills/tests/tasks/uipath-rpa/` | Implemented |

## Adding New Benchmarks

### Adding to the Canonical Suite

1. Open `uipath_claude/evaluation/datasets.py`
2. Add a new `Example` object to the `from_workflow_benchmarks` method
3. Ensure you define the `inputs`, `outputs` (expected files, packages, activities, trajectory), and `metadata`

### Adding Coder-Eval Tests

1. Create YAML task in `skills/tests/tasks/<skill-name>/`
2. Follow the task structure in `skills/tests/README.md`
3. Run with `make test-<skill-name>`
