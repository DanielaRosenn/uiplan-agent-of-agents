# Evaluation CLI Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 41 failing evaluation tests by improving CLI output indicators and evaluation parser accuracy.

**Architecture:** Add structured markers to CLI output (`[TOOL_CALL: name]`, `[SKILL: name]`, `[PLANNING]`, `[EXECUTING]`) that the evaluation parser can reliably extract. Auto-approve plans when stdin is non-interactive. Increase timeout and ensure sample_project has valid project.json.

**Tech Stack:** Python, typer CLI, Rich console, regex parsing

---

## File Structure

| File | Responsibility |
|------|----------------|
| `uipath_claude/cli/app.py` | Add `--auto-approve-plan` flag, detect non-interactive stdin, print `[EXECUTING]` always |
| `uipath_claude/rendering/progress.py` | Add `[TOOL_CALL: name]` and `[SKILL: name]` markers |
| `docs/evaluations/run_evaluations.py` | Fix tool/mode parsing, increase timeout, remove `--no-plan` |
| `docs/evaluations/HOW_TO_RUN_TESTS.md` | Document markers and auto-approve behavior |

---

### Task 1: Add [TOOL_CALL: name] Marker to Progress Reporter

**Files:**
- Modify: `uipath_claude/rendering/progress.py:256-278`

- [ ] **Step 1: Add [TOOL_CALL: name] marker before human-readable description**

Open `uipath_claude/rendering/progress.py` and find the `tool_call` method (around line 256). Add a structured marker that the parser can extract:

```python
def tool_call(self, name: str, args: dict) -> None:
    """
    Show tool being called with icon.

    Args:
        name: Tool name
        args: Tool arguments
    """
    # Structured marker for evaluation parser (must be on its own line)
    self.console.print(f"[dim][TOOL_CALL: {name}][/dim]")
    
    # Map tool names to human-readable descriptions
    tool_descriptions = {
        "ensure_project_structure": "Creating project structure",
        "write_file": "Writing file",
        "read_file": "Reading file",
        "validate_file": "Validating file",
        "install_package": "Installing NuGet package",
        "find_activity_info": "Looking up activity info",
        "query_uipath_docs": "Searching UiPath docs",
        "validate_and_fix_loop": "Validating and fixing",
        "list_files": "Listing files",
        "run_workflow": "Running workflow",
        "deploy_to_orchestrator": "Deploying to Orchestrator",
    }
    
    description = tool_descriptions.get(name, name)
    self.console.print(f"  [cyan]->[/cyan] {description}")
    
    # Show key arguments (always show something useful)
    if "file_path" in args:
        self.console.print(f"     [dim]File: {args['file_path']}[/dim]")
    elif "package_id" in args:
        self.console.print(f"     [dim]Package: {args['package_id']}[/dim]")
    elif "query" in args:
        query = args["query"]
        if len(query) > 60:
            query = query[:60] + "..."
        self.console.print(f"     [dim]Query: {query}[/dim]")
    elif "project_name" in args:
        self.console.print(f"     [dim]Project: {args['project_name']}[/dim]")
    
    # Show full args in verbose mode
    if self.verbose or self.raw:
        import json
        args_str = json.dumps(args, indent=2)
        if not self.verbose and len(args_str) > 300:
            args_str = args_str[:300] + "..."
        self.console.print(f"     [dim]{args_str}[/dim]")
```

- [ ] **Step 2: Verify the change compiles**

Run: `python -c "from uipath_claude.rendering.progress import AgenticProgressReporter; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add uipath_claude/rendering/progress.py
git commit -m "$(cat <<'EOF'
feat(cli): add [TOOL_CALL: name] marker for evaluation parser

Adds a structured marker line before each tool call that the
evaluation parser can reliably extract using regex.
EOF
)"
```

---

### Task 2: Add [SKILL: name] Marker When Skills Are Invoked

**Files:**
- Modify: `uipath_claude/rendering/progress.py:171-182`

- [ ] **Step 1: Add [SKILL: name] marker in skills_in_context method**

Find the `skills_in_context` method (around line 171) and add a structured marker:

```python
def skills_in_context(self, names: list[str], primary_skill: str) -> None:
    """Print selected skills once per agentic run (when names non-empty)."""
    cleaned = [str(n).strip() for n in names if str(n).strip()]
    if not cleaned:
        return
    
    # Structured marker for evaluation parser
    for skill_name in cleaned:
        self.console.print(f"[dim][SKILL: {skill_name}][/dim]")
    
    line = ", ".join(cleaned)
    extra = ""
    ps = str(primary_skill).strip() if primary_skill else ""
    if ps and ps != cleaned[0]:
        extra = f" — primary: {ps}"
    self.console.print(f"[dim]Skills in context:[/dim] [cyan]{line}[/cyan]{extra}")
    self.console.print()
```

- [ ] **Step 2: Verify the change compiles**

Run: `python -c "from uipath_claude.rendering.progress import AgenticProgressReporter; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add uipath_claude/rendering/progress.py
git commit -m "$(cat <<'EOF'
feat(cli): add [SKILL: name] markers for evaluation parser

Emits [SKILL: name] for each skill in context so evaluations
can track which skills were invoked.
EOF
)"
```

---

### Task 3: Ensure [EXECUTING] Marker is Always Printed

**Files:**
- Modify: `uipath_claude/cli/app.py:1048-1062`

- [ ] **Step 1: Move [EXECUTING] print outside the conditional blocks**

Find the execution section (around line 1048) and ensure `[EXECUTING]` is always printed before invoking the chat graph:

```python
            # Check if agentic mode is enabled (has its own progress output)
            agentic_mode_on = os.environ.get("UIPATH_AGENTIC_MODE", "1").lower() in ("1", "true", "yes")
            debug_mode_on = os.environ.get("UIPATH_DEBUG_AGENT", "1").lower() in ("1", "true", "yes")
            use_spinner = not (agentic_mode_on and debug_mode_on)
            
            # Always print [EXECUTING] marker for evaluation parser
            console.print("[bold yellow][EXECUTING][/bold yellow]")
        
            if use_spinner and (stream_enabled and suppress_stream_output):
                with progress.generating("workflow"):
                    result = asyncio.run(chat_graph.ainvoke(invocation))
            elif use_spinner and (not stream_enabled and file_intent):
                with progress.generating("workflow"):
                    result = asyncio.run(chat_graph.ainvoke(invocation))
            else:
                result = asyncio.run(chat_graph.ainvoke(invocation))
```

- [ ] **Step 2: Verify the change compiles**

Run: `python -c "from uipath_claude.cli import app; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add uipath_claude/cli/app.py
git commit -m "$(cat <<'EOF'
feat(cli): always print [EXECUTING] marker

Moves the [EXECUTING] marker outside conditional blocks so it
is always emitted, making mode detection reliable for evaluations.
EOF
)"
```

---

### Task 4: Auto-Approve Plans When Stdin is Non-Interactive

**Files:**
- Modify: `uipath_claude/cli/app.py:658-668` (add flag)
- Modify: `uipath_claude/cli/app.py:989-1010` (use flag + isatty check)

- [ ] **Step 1: Add --auto-approve-plan CLI flag**

Find the `chat` function definition (around line 658) and add the new flag:

```python
@app.command()
def chat(
    no_banner: bool = typer.Option(False, "--no-banner", help="Skip welcome banner"),
    no_plan: bool = typer.Option(False, "--no-plan", help="Skip planning phase for BUILD intents"),
    auto_approve_plan: bool = typer.Option(
        False,
        "--auto-approve-plan",
        help="Auto-approve plans without prompting (for CI/testing)",
    ),
    stream: bool | None = typer.Option(
        None,
        "--stream/--no-stream",
        help="Stream assistant tokens while generating responses.",
    ),
    track_processes: bool = typer.Option(True, "--track-processes/--no-track-processes", help="Track and cleanup only test-opened Studio processes"),
):
```

- [ ] **Step 2: Auto-approve when flag is set or stdin is non-interactive**

Find the plan approval prompt (around line 989) and modify it to auto-approve:

```python
                    from rich.markdown import Markdown
                    from rich.panel import Panel
                    console.print(Panel(Markdown(plan_result.final_response), title="Implementation Plan", border_style="cyan"))
                    
                    # Auto-approve if flag set or stdin is non-interactive (piped)
                    is_interactive = sys.stdin.isatty()
                    if auto_approve_plan or not is_interactive:
                        console.print("[dim]Auto-approving plan (non-interactive mode)[/dim]")
                        confirm = "y"
                    else:
                        confirm = Prompt.ask("Approve plan? [y/n/edit]", default="y").strip().lower()
                    
                    if confirm in ("y", "yes"):
                        approved_plan = plan_result.final_response
                        # Save plan to file
                        plan_path = _save_plan_to_file(
                            session_id=chat_session_id,
                            user_request=user_input,
                            plan_content=approved_plan,
                            output_root=_get_output_root(),
                        )
                        console.print(f"[dim]Plan saved to: {plan_path}[/dim]")
                        break
                    elif confirm in ("n", "no"):
                        progress.info("Plan cancelled.")
                        break
                    else:
                        # Treat other input as feedback
                        user_input = f"{user_input}\n\nFeedback on plan: {confirm}"
                        continue
```

- [ ] **Step 3: Add sys import if not present**

Check the imports at the top of `app.py`. If `sys` is not imported, add it:

```python
import sys
```

- [ ] **Step 4: Verify the change compiles**

Run: `python -c "from uipath_claude.cli import app; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/cli/app.py
git commit -m "$(cat <<'EOF'
feat(cli): auto-approve plans in non-interactive mode

Adds --auto-approve-plan flag and auto-approves when stdin is
not a TTY (piped input). This allows evaluations to test the
full planning flow without hanging on the approval prompt.
EOF
)"
```

---

### Task 5: Update Evaluation Runner - Remove --no-plan, Update Parser

**Files:**
- Modify: `docs/evaluations/run_evaluations.py:59-66` (CLI args)
- Modify: `docs/evaluations/run_evaluations.py:122-128` (tool call parser)
- Modify: `docs/evaluations/run_evaluations.py:181-192` (mode detection)

- [ ] **Step 1: Remove --no-plan from CLI invocation**

Find the subprocess.Popen call (around line 59) and remove `--no-plan`:

```python
            process = subprocess.Popen(
                [
                    "uipath-claude",
                    "chat",
                    "--no-banner",
                    "--track-processes",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=self.project_dir,
                env=env,
            )
```

- [ ] **Step 2: Fix tool call extraction to use [TOOL_CALL: name] marker**

Find `extract_tool_calls` (around line 122) and update the regex:

```python
@staticmethod
def extract_tool_calls(stdout: str) -> list[str]:
    """Extract tool calls from output using structured markers."""
    tools = []
    # Primary: structured [TOOL_CALL: name] markers
    for match in re.finditer(r'\[TOOL_CALL:\s*(\w+)\]', stdout):
        tools.append(match.group(1))
    # Fallback: old -> pattern (for backwards compatibility)
    if not tools:
        for match in re.finditer(r'->\s+(\w+)', stdout):
            tool = match.group(1)
            # Filter out non-tool names
            if tool.lower() not in ('skills', 'searching', 'creating', 'validating', 'writing', 'responding'):
                tools.append(tool)
    return tools
```

- [ ] **Step 3: Add skill extraction method**

Add a new method after `extract_tool_calls`:

```python
@staticmethod
def extract_skills(stdout: str) -> list[str]:
    """Extract invoked skills from output using structured markers."""
    skills = []
    for match in re.finditer(r'\[SKILL:\s*([^\]]+)\]', stdout):
        skills.append(match.group(1).strip())
    return skills
```

- [ ] **Step 4: Update mode detection to use [PLANNING] and [EXECUTING] markers**

Find `detect_mode` (around line 181) and update it:

```python
@staticmethod
def detect_mode(stdout: str) -> str:
    """Detect which mode the agent used from structured markers."""
    has_planning = '[PLANNING]' in stdout
    has_executing = '[EXECUTING]' in stdout
    
    if has_planning and has_executing:
        return 'planning_then_execution'
    if has_planning:
        return 'planning'
    if has_executing:
        return 'execution'
    
    # Fallback heuristics
    if '?' in stdout and 'clarif' in stdout.lower():
        return 'clarification'
    return 'direct_response'
```

- [ ] **Step 5: Update parsed output to include skills**

Find the `run_evaluation` function (around line 366) and add skills to parsed output:

```python
    # Parse output
    parsed = {
        'stdout': cli_result['stdout'],
        'stderr': cli_result['stderr'],
        'crashed': cli_result.get('crashed', False),
        'tool_calls': OutputParser.extract_tool_calls(cli_result['stdout']),
        'skills': OutputParser.extract_skills(cli_result['stdout']),
        'files_written': OutputParser.extract_files_written(cli_result['stdout']),
        'errors': OutputParser.extract_errors(cli_result['stdout'], cli_result['stderr']),
        'mode': OutputParser.detect_mode(cli_result['stdout']),
        'response': OutputParser.extract_assistant_response(cli_result['stdout'])
    }
```

- [ ] **Step 6: Update result output to include skills**

Find where parsed data is added to the result dict (around line 395) and add skills:

```python
        'parsed': {
            'mode': parsed['mode'],
            'tool_calls': parsed['tool_calls'],
            'skills': parsed.get('skills', []),
            'files_written': parsed['files_written'],
            'errors': parsed['errors'][:20],
            'assistant_response_preview': (parsed['response'] or '')[:2000],
        },
```

- [ ] **Step 7: Verify syntax**

Run: `python -m py_compile docs/evaluations/run_evaluations.py`
Expected: No output (success)

- [ ] **Step 8: Commit**

```bash
git add docs/evaluations/run_evaluations.py
git commit -m "$(cat <<'EOF'
fix(eval): update parser for structured CLI markers

- Remove --no-plan flag (CLI auto-approves when stdin is piped)
- Parse [TOOL_CALL: name] markers for reliable tool detection
- Parse [SKILL: name] markers to track skill invocations
- Update mode detection to use [PLANNING]/[EXECUTING] markers
EOF
)"
```

---

### Task 6: Increase Default Timeout

**Files:**
- Modify: `docs/evaluations/run_evaluations.py:37` (default timeout in CLITestRunner)
- Modify: `docs/evaluations/run_evaluations.py:451-454` (argparse default)

- [ ] **Step 1: Increase CLITestRunner default timeout to 180s**

Find the `__init__` method (around line 37):

```python
def __init__(self, project_dir: str | None = None, timeout: int = 180):
    repo_root = Path(__file__).resolve().parent.parent.parent
    self.project_dir = project_dir or str(repo_root / "tests" / "fixtures" / "sample_project")
    self.timeout = timeout
```

- [ ] **Step 2: Update argparse default to match**

Find the `--timeout` argument (around line 451):

```python
parser.add_argument(
    '--timeout',
    type=int,
    default=180,
    help='Per-test CLI timeout in seconds (default: 180)',
)
```

- [ ] **Step 3: Verify syntax**

Run: `python -m py_compile docs/evaluations/run_evaluations.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add docs/evaluations/run_evaluations.py
git commit -m "$(cat <<'EOF'
fix(eval): increase default timeout to 180s

Planning mode adds overhead; 120s was too tight for complex builds.
EOF
)"
```

---

### Task 7: Run Single Test to Verify Fixes

**Files:**
- None (verification only)

- [ ] **Step 1: Run a simple question test (should pass quickly)**

Run: `python docs/evaluations/run_evaluations.py --test QA-001`
Expected: 
- Output shows `[EXECUTING]` marker
- Technical: PASS
- Conceptual: PASS

- [ ] **Step 2: Run a BUILD test to verify planning flow**

Run: `python docs/evaluations/run_evaluations.py --test BUILD-001 --timeout 300`
Expected:
- Output shows `[PLANNING]` marker
- Output shows `[EXECUTING]` marker
- Shows `[TOOL_CALL: write_file]` or similar
- Mode detected as `planning_then_execution`

- [ ] **Step 3: Check per-test JSON for correct parsing**

Run: `python -c "import json; d=json.load(open('docs/evaluations/results/BUILD-001.json')); print('mode:', d['result']['parsed']['mode']); print('tools:', d['result']['parsed']['tool_calls'])"`
Expected:
- mode: `planning_then_execution`
- tools: includes `write_file`

- [ ] **Step 4: Document results**

If tests pass, proceed. If failures, debug before continuing.

---

### Task 8: Update test_cases.json Expectations (If Needed)

**Files:**
- Modify: `docs/evaluations/test_cases.json` (only if expectations need adjustment)

- [ ] **Step 1: Review failing tests after running full suite**

Run: `python docs/evaluations/run_evaluations.py --timeout 300`
Wait for completion (may take 30-60 minutes).

- [ ] **Step 2: Check TRIAGE.md for remaining failures**

Read: `docs/evaluations/results/TRIAGE.md`
List any tests that still fail and note why.

- [ ] **Step 3: Adjust test expectations if CLI behavior is correct**

For any test where CLI behavior is correct but expectation is wrong, update `test_cases.json`. Example: if a test expects `execution` but CLI correctly does `planning_then_execution`:

```json
{
  "test_id": "EXAMPLE-001",
  "expected": {
    "technical": {
      "mode": "planning_then_execution"
    }
  }
}
```

- [ ] **Step 4: Commit any expectation fixes**

```bash
git add docs/evaluations/test_cases.json
git commit -m "$(cat <<'EOF'
fix(eval): align test expectations with planning mode behavior

Updated mode expectations to planning_then_execution for BUILD
tests now that --no-plan is removed from evaluation runner.
EOF
)"
```

---

### Task 9: Update HOW_TO_RUN_TESTS.md Documentation

**Files:**
- Modify: `docs/evaluations/HOW_TO_RUN_TESTS.md`

- [ ] **Step 1: Document the structured markers**

Add a section explaining the CLI markers:

```markdown
## CLI Output Markers

The CLI emits structured markers that the evaluation parser uses:

| Marker | Meaning |
|--------|---------|
| `[PLANNING]` | Planning phase started |
| `[EXECUTING]` | Execution phase started |
| `[TOOL_CALL: name]` | Tool `name` was invoked |
| `[SKILL: name]` | Skill `name` is in context |

These markers appear in CLI output and are parsed by `run_evaluations.py` to determine test pass/fail.
```

- [ ] **Step 2: Document auto-approve behavior**

Add to the running tests section:

```markdown
## Non-Interactive Mode

When stdin is not a TTY (e.g., piped input from tests), the CLI automatically:
- Approves plans without prompting
- Uses the `--auto-approve-plan` flag behavior

This allows evaluations to test the full planning flow without manual intervention.
```

- [ ] **Step 3: Commit**

```bash
git add docs/evaluations/HOW_TO_RUN_TESTS.md
git commit -m "$(cat <<'EOF'
docs: document CLI markers and auto-approve behavior
EOF
)"
```

---

## Summary

After completing all tasks:

1. CLI emits `[TOOL_CALL: name]`, `[SKILL: name]`, `[PLANNING]`, and `[EXECUTING]` markers
2. Evaluation parser extracts these reliably
3. Planning mode runs during evaluations (auto-approved)
4. Timeout increased to 180s
5. Tests should pass at a much higher rate

Run final verification:
```bash
python docs/evaluations/run_evaluations.py --timeout 300
```

Compare pass rate to baseline (was 18%, target >70%).
