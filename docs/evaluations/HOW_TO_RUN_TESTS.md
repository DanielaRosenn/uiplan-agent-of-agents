# How to Run CLI Evaluations

## Prerequisites

1. **UiPath project directory** - Tests should run from a directory with `project.json`
2. **Environment variables set**:
   ```bash
   export UIPATH_SKIP_AUTH_CHECK=1    # Skip interactive auth prompts
   export PYTHONIOENCODING=utf-8      # Handle Unicode
   ```

## Always close Studio after each test (required policy)

Long test batches must **not** leave `UiPath.Studio.exe` / `UiPath.Executor.exe` running between cases, or the machine will be overloaded.

### When using `run_evaluations.py` (default)

- After **every** test (success, failure, or **timeout**), the runner **always** runs parent-side cleanup: it snapshots UiPath-related PIDs before the subprocess, then terminates any **new** Studio/Executor processes that appeared during that test.
- This runs in a `finally` block so it still runs if the child CLI is **killed** on timeout (the child may never reach its own `finally`).
- The subprocess is also started with **`--track-processes`** so the CLI’s own session cleanup stays enabled when the process exits normally.
- Console lines like `[cleanup] Closed N UiPath process(es): ...` confirm cleanup ran.

**What gets closed:** Only processes that **started after** the per-test snapshot (typically Studio/Executor opened during that run). Instances you already had open **before** the test began should keep the same PID and are not targeted.

### When running `uipath-claude chat` manually

- Use **`--track-processes`** (this is the default; avoid `--no-track-processes` unless you intentionally want to leave Studio open).
- Always end the session with **`exit`** so the chat `finally` block can run and close Studio instances opened during that session.
- If you **kill** the CLI process (Task Manager, `taskkill`, or a harness timeout without cleanup), run your own cleanup or use `run_evaluations.py` patterns: snapshot PIDs before/after and terminate new `UiPath.Studio.exe` / `UiPath.Executor.exe` PIDs.

## Running a Single Test Manually

### Step 1: Navigate to a UiPath project directory

```powershell
cd tests\fixtures\sample_project
```

### Step 2: Set environment variables

```powershell
$env:UIPATH_SKIP_AUTH_CHECK = "1"
$env:PYTHONIOENCODING = "utf-8"
```

### Step 3: Run the CLI with test input

```powershell
echo "YOUR_TEST_INPUT`nexit" | uipath-claude chat --no-banner --no-plan --track-processes 2>&1
```

**Flags explained:**
- `--no-banner`: Skip welcome banner (cleaner output)
- `--no-plan`: Skip planning mode approval prompts
- `--track-processes`: On session exit, close Studio/Executor processes opened during **this** chat session (default; keep explicit for copy-paste safety)
- `2>&1`: Capture both stdout and stderr

### Step 4: Capture and evaluate output

Save output to file for analysis:
```powershell
echo "What is project.json?`nexit" | uipath-claude chat --no-banner --no-plan --track-processes 2>&1 > results\QA-001_output.txt
```

## Running Tests with the Evaluation Script

From the **repository root**:

```powershell
python docs/evaluations/run_evaluations.py
```

This runs **all** cases in `test_cases.json` and writes:

| Output | Path |
|--------|------|
| Per-test log | `docs/evaluations/results/<TEST_ID>.json` |
| Aggregate summary | `docs/evaluations/results/run_summary.json` |
| Triage table | `docs/evaluations/results/TRIAGE.md` |

Options:

```powershell
# One test
python docs/evaluations/run_evaluations.py --test QA-001

# Several tests by id (repeat --test)
python docs/evaluations/run_evaluations.py --test QA-001 --test QA-002 --test DEPLOY-001

# Category
python docs/evaluations/run_evaluations.py --category "Workflow Building"

# Custom project dir (timeout auto-set by category: e.g. Workflow Building=300s,
# Question=180s, Learning=120s, Validation=180s; see CATEGORY_TIMEOUTS in run_evaluations.py)
python docs/evaluations/run_evaluations.py --project-dir tests\fixtures\sample_project

# Override timeout for all tests (ignores category defaults)
python docs/evaluations/run_evaluations.py --timeout 600

# Custom log directory + full JSON dump
python docs/evaluations/run_evaluations.py --log-dir docs/evaluations/results/run_20260416 --output docs/evaluations/results/full_dump.json
```

**Note:** A full run of the default batch (all cases except deferred full-project E2E) can take a long time (roughly N x timeout cap). Run in a dedicated terminal or background job.

**Full-project E2E (last 4 cases in `test_cases.json`):** Marked with `"skip_in_default_batch": true` (`E2E-FP-001` … `E2E-FP-004`). Default run **excludes** them.

```powershell
# Default: all cases except the four full-project E2E tests
python docs/evaluations/run_evaluations.py

# Only the four full-project E2E tests
python docs/evaluations/run_evaluations.py --only-full-project-e2e --timeout 300

# Entire suite including E2E
python docs/evaluations/run_evaluations.py --include-full-project-e2e
```

See **[Always close Studio after each test](#always-close-studio-after-each-test-required-policy)** above for full detail.

## Example Test Execution: QA-001

### Test Case
```json
{
  "test_id": "QA-001",
  "input": "What is project.json?",
  "expected": {
    "technical": {
      "mode": "direct_response",
      "tool_calls_required": [],
      "no_file_creation": true
    },
    "conceptual": {
      "response_must_contain_all": ["project.json"],
      "response_must_explain": ["configuration", "dependencies"]
    }
  }
}
```

### Command
```powershell
cd tests\fixtures\sample_project
$env:UIPATH_SKIP_AUTH_CHECK = "1"
echo "What is project.json?`nexit" | uipath-claude chat --no-banner --no-plan --track-processes 2>&1
```

### Output Parsing

Look for these indicators in the output:

| Indicator | Pattern | Meaning |
|-----------|---------|---------|
| Mode | `[PLANNING]` or `[EXECUTING]` | Which mode agent used |
| Tool calls | `-> tool_name` | Tools invoked |
| Files written | `Wrote:` or `Created` | Artifacts created |
| Errors | `x Error:` | Tool errors |
| Response | After `Assistant:` | Final response |

### Evaluation

**Technical Stage:**
- Check mode matches expected
- Check required tools were called
- Check files created match expected
- Verify no crash (no `Traceback` in stderr)

**Conceptual Stage:**
- Check response contains required phrases
- Check response explains expected concepts
- Verify no forbidden phrases appear

## Test Result Format

Save results as JSON in `results/` folder:

```json
{
  "test_id": "QA-001",
  "execution_timestamp": "2026-04-16T08:04:30Z",
  "parsed_output": {
    "mode_detected": "execution",
    "tool_calls": ["read_project_json"],
    "assistant_response": "..."
  },
  "evaluation": {
    "technical": { "passed": false, "failures": [...] },
    "conceptual": { "passed": true },
    "overall_passed": false
  }
}
```

## Category-Based Timeouts

The runner automatically selects an appropriate timeout based on test category:

| Category | Timeout | Rationale |
|----------|---------|-----------|
| Workflow Building | 300s (5 min) | Planning + multi-step execution |
| Workflow Modification | 300s (5 min) | Planning + file edits |
| Build and Deploy | 420s (7 min) | Planning + build + Orchestrator deploy |
| Question | 60s (1 min) | Direct Q&A, no planning |
| Error Handling | 90s (1.5 min) | Error detection scenarios |
| Code Generation | 240s (4 min) | Planning + code generation |
| (other) | 180s (3 min) | Default fallback |

Use `--timeout N` to override all category defaults with a fixed value.

## Documentation-Driven Development

The agent now supports automatic documentation detection and creation for complex projects.

### Documentation Types

| Type | Agent | Purpose |
|------|-------|---------|
| PDD | Business Analyst | Process Definition Document - business requirements |
| SDD | Solution Architect | Solution Design Document - technical architecture |
| ADD | Solution Architect | Agent Design Document - AI/agentic components |
| TDD | Solution Architect | Technical Design Document - implementation specs |

### How It Works

1. **Intent Detection**: The intent classifier detects explicit documentation requests ("Create a PDD", "Help me document this process")

2. **Complexity Analysis**: For build requests, the system analyzes complexity indicators:
   - Integration keywords (Salesforce, SAP, API, database)
   - Human approval keywords (manager, approve, review)
   - AI/Agent keywords (LLM, Claude, agent)
   - Compliance keywords (GDPR, audit, security)

3. **Routing**: Based on the analysis:
   - PDD requests → Business Analyst agent
   - SDD/ADD/TDD requests → Solution Architect agent
   - PDD is always created before technical docs

4. **Persistence**: Documentation is saved to the project's `docs/` folder

### CLI Markers

- `[DOC_PHASE: TYPE]` - Entering documentation creation phase
- `[DOC_CREATED: TYPE]` - Documentation file created
- `[SKILL: uipath-ba]` - Business Analyst agent active
- `[SKILL: uipath-sa-sdd]` - Solution Architect agent active

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `UIPATH_BA_MAX_ITERATIONS` | 15 | Max iterations for BA agent |
| `UIPATH_SA_MAX_ITERATIONS` | 15 | Max iterations for SA agent |

### Example Usage

```bash
# Explicit documentation request
uipath-claude chat
You: Create a PDD for invoice processing

# Complex project triggers documentation recommendation
You: Build enterprise invoice processing with SAP integration and manager approvals
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Test hangs | Planning + long agent loop | Category timeouts should handle this; or `UIPATH_PLANNER_MAX_ITERATIONS` (runner defaults to 10) |
| Empty `stdout` in JSON on timeout (Windows) | `communicate()` does not attach partial streams to `TimeoutExpired` | Runner uses background line readers so partial output is kept; plus `python -u` and CLI line-buffering when not a TTY |
| Auth prompt | Interactive auth | Set `UIPATH_SKIP_AUTH_CHECK=1` |
| Unicode errors | Windows encoding | Set `PYTHONIOENCODING=utf-8` |
| project.json not found | Wrong directory | Run from project directory |
| Timeout | Long execution | Use `--timeout N` override, or check LLM response times |
| Many Studio windows after a batch | Harness did not run parent cleanup | Use `run_evaluations.py` or replicate its PID snapshot + kill-new-Studio logic after each subprocess |

## CLI Output Markers

The CLI emits structured markers that the evaluation parser uses:

| Marker | Meaning |
|--------|---------|
| `[PLANNING]` | Planning phase started |
| `[EXECUTING]` | Execution phase started |
| `[TOOL_CALL: name]` | Tool `name` was invoked |
| `[SKILL: name]` | Skill `name` is in context |

These markers appear in CLI output and are parsed by `run_evaluations.py` to determine test pass/fail.

## Non-Interactive Mode

When stdin is not a TTY (e.g., piped input from tests), the CLI automatically:
- Approves plans without prompting
- Uses the `--auto-approve-plan` flag behavior

This allows evaluations to test the full planning flow without manual intervention.

## Evaluation child process and planner cap

`run_evaluations.py` starts chat with **`sys.executable -u`** and `from uipath_claude.cli.app import app` so output is not stuck in a full pipe buffer for the whole run.

Unless you set it yourself, the runner exports **`UIPATH_PLANNER_MAX_ITERATIONS=10`** so the read-only planner uses at most 10 ReAct steps (the main chat agent still uses `UIPATH_MAX_ITERATIONS`, default 25). Override in the environment before running if you need a different cap.

## Directory Structure

```
docs/evaluations/
├── test_cases.json       # Test definitions (default batch + deferred E2E)
├── run_evaluations.py    # Automated runner
├── HOW_TO_RUN_TESTS.md   # This file
├── README.md             # Overview
└── results/              # Test execution results
    └── QA-001_execution.json
```
