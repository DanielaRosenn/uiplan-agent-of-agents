# UiPath Claude CLI Evaluation Framework

## Overview

This folder contains the evaluation framework for testing the `uipath-claude chat` CLI with two-stage evaluation:

1. **Technical Stage**: Verifies the agentic flow (tool calls, artifacts, error handling)
2. **Conceptual Stage**: Evaluates response quality (content accuracy, helpfulness)

## Files

- `test_cases.json` - Test case definitions with specific expected outputs
- `run_evaluations.py` - Evaluation runner script
- `results/` - Output folder for evaluation results

## Test Case Structure

```json
{
  "test_id": "BUILD-001",
  "category": "Workflow Building",
  "input": "Create a workflow that logs Hello World",
  "preconditions": {
    "requires_project": false,
    "requires_auth": false,
    "env_vars": []
  },
  "expected": {
    "technical": {
      "mode": "planning_then_execution",
      "tool_calls_required": ["write_file"],
      "artifacts": {
        "files_created": ["*.xaml"],
        "xaml_must_contain": ["LogMessage", "Hello World"]
      },
      "crash_not_allowed": true
    },
    "conceptual": {
      "response_must_contain_all": ["Created", "workflow"],
      "response_must_not_contain": ["error", "failed"],
      "expected_response_pattern": "Created {workflow}.xaml with Log Message..."
    }
  }
}
```

## Evaluation Criteria

### Technical Stage

| Check | Description |
|-------|-------------|
| `mode` | Expected mode: `planning_then_execution`, `execution`, `direct_response`, `clarification` |
| `tool_calls_required` | Tools that MUST be called |
| `tool_calls_optional` | Tools that MAY be called |
| `artifacts.files_created` | Files that must be created (glob patterns) |
| `artifacts.xaml_must_contain` | Strings that must appear in generated XAML |
| `crash_not_allowed` | Test fails if unhandled exception occurs |
| **Routing (Subagent / persona)** | |
| `skills_required` | Substrings that must appear in parsed `[SKILL: ...]` lines (case-insensitive; flexible matching) |
| `skills_forbidden` | Skill markers that must **not** appear |
| `document_type_required` | Document-output marker (`ADD` or `TDD`) that must appear in parsed `[DOCUMENT_TYPE: ...]` lines |
| `document_type_forbidden` | Document-output markers (`ADD` / `TDD`) that must **not** appear |
| `routing_expected` | Informational note only (logged as pass detail; does not fail tests) |
| `no_file_creation` | Fail routing if any file write was detected |
| `artifacts_forbidden` | Glob-like patterns (`*.xaml`) or substrings against written paths |
| `safety_forbidden_phrases` | Phrases that must **not** appear in assistant response + stderr (case-insensitive). This intentionally ignores the user's prompt so tests can include unsafe examples without failing on the input itself. |
| `routing_failure_is_blocking` | If `true`, routing failures fail the technical stage. If omitted: blocking when any routing key above is set except `routing_expected`. |

Routing failures are counted separately (`routing_checks_failed`, `routing_passed` in JSON) from execution/tool failures.

### Conceptual Stage

| Check | Description |
|-------|-------------|
| `response_must_contain_all` | ALL of these strings must appear in response |
| `response_must_contain_any` | AT LEAST ONE of these strings must appear |
| `response_must_not_contain` | NONE of these strings should appear |
| `response_should_mention` | Strings that should appear (warning if missing) |
| `expected_response_pattern` | Template showing ideal response structure |

## Running Evaluations

```bash
# Run all tests
python run_evaluations.py

# Run specific category
python run_evaluations.py --category "Workflow Building"

# Run single test
python run_evaluations.py --test BUILD-001

# Output results to JSON
python run_evaluations.py --output results/run_$(date +%Y%m%d).json
```

## Adding New Test Cases

1. Add test case to `test_cases.json`
2. Include specific expected outputs for both stages
3. Run evaluation to verify test case works

## Categories

- **Workflow Building**: Creating new XAML workflows
- **Deployment**: Deploying to Orchestrator
- **Question**: Answering UiPath-related questions
- **Clarification**: Handling ambiguous requests
- **Authentication**: Auth status and login flows
- **Error Handling**: Graceful error handling
- **Complex Scenario**: Multi-step workflows
- **Edge Case**: Unusual inputs
- **Modification**: Editing existing workflows
- **Library**: Documentation library MCP tools (`list_library_books`, `search_library`, …)
- **Subagent Routing**: Persona/subagent/document-output scenarios; uses routing fields plus conceptual checks. Seed cases use **`skip_in_default_batch`: true** — run with `--category "Subagent Routing"` or `--test SUB-…`

See [`SUBAGENT_PERSONA_MATRIX.md`](SUBAGENT_PERSONA_MATRIX.md) for cohort IDs and Academy-aligned roles vs document outputs (ADD/TDD under SA).
