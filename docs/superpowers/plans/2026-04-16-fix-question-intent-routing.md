# Fix QUESTION Intent Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up `simple_llm_answer` for `QUESTION` intents so simple questions bypass the agentic graph and planning logic.

**Architecture:** Add a conditional branch in the CLI chat loop (before planning/graph invocation) that detects `QUESTION` intent and calls `simple_llm_answer` directly, then skips to the next turn.

**Tech Stack:** Python, `langchain-aws` (`ChatBedrockConverse`), existing `simple_answer.py` module.

---

## File Map

- **Modify**: `uipath_claude/cli/app.py` — Add `QUESTION` routing before planning block
- **Use (no changes)**: `uipath_claude/query/simple_answer.py` — Already implemented
- **Use (no changes)**: `uipath_claude/query/intent_classifier.py` — Already classifies `QUESTION` correctly
- **Test**: `tests/unit/cli/test_app.py` — Add test for `QUESTION` routing (if test file exists)

---

## Task 1: Add QUESTION routing in CLI chat loop

**Files:**
- Modify: `uipath_claude/cli/app.py:992-1095` (around the planning block and graph invocation)
- Test: `tests/unit/cli/test_app.py` (if exists, or manual CLI test)

- [x] **Step 1: Import `simple_llm_answer` at top of `app.py`**

Add this import near the other query module imports (likely around line 30–50):

```python
from uipath_claude.query.simple_answer import simple_llm_answer
```

- [x] **Step 2: Add QUESTION routing logic before planning block**

Insert this block **immediately after** line 992 (where `intent, intent_reason = classify_intent(user_input)`) and **before** the "Plan Mode logic" comment (line 993):

```python
            # QUESTION intents bypass planning and agentic graph
            if intent == IntentType.QUESTION:
                console.print("[bold cyan][ANSWERING][/bold cyan]")
                _flush_stdio()
                
                def _print_delta(delta: str) -> None:
                    console.print(delta, end="")
                
                stream_callback = _print_delta if stream_enabled else None
                console.print("[magenta]Assistant:[/magenta] ", end="")
                
                try:
                    answer = asyncio.run(
                        simple_llm_answer(
                            user_input=user_input,
                            history=history,
                            model_name=model_name,
                            region=region,
                            stream=stream_enabled,
                            on_delta=stream_callback,
                        )
                    )
                    if not stream_enabled:
                        console.print(answer, end="")
                    console.print("")  # newline
                    
                    # Update history
                    history.append({"role": "user", "content": user_input})
                    history.append({"role": "assistant", "content": answer})
                    
                    # Skip to next turn
                    continue
                except Exception as exc:
                    progress.error("Simple answer failed")
                    console.print(f"Error: {exc}")
                    continue
```

Expected: The CLI now prints `[ANSWERING]` for `QUESTION` intents and calls `simple_llm_answer`.

- [x] **Step 3: Verify imports and flush are available**

Ensure these are defined earlier in `app.py`:
- `_flush_stdio()` (should be defined around line 200–300)
- `console` (Rich Console instance)
- `progress` (progress object)
- `asyncio`, `history`, `model_name`, `region`, `stream_enabled` (should all be in scope in the chat loop)

Run: `rg "_flush_stdio|def _flush_stdio" uipath_claude/cli/app.py`
Expected: Function definition found.

- [x] **Step 4: Manually test with a simple question**

Run:
```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
python -m uipath_claude.cli.app --no-plan
```

At the prompt, type: `What is project.json?`

Expected output:
```
[ANSWERING]
Assistant: project.json is a configuration file that defines UiPath project metadata...
```

NO `[PLANNING]` or "Implementation Plan" panel should appear.

- [x] **Step 5: Test another question to verify behavior**

At the same CLI prompt, type: `How does Main.xaml work?`

Expected: `[ANSWERING]` marker + simple explanation, no planning.

- [x] **Step 6: Test that BUILD intents still trigger planning**

At the same CLI prompt (or restart without `--no-plan`), type: `Create an Excel reader workflow`

Expected: `[PLANNING]` + "Implementation Plan" panel + "Approve plan?" prompt (if not using `--no-plan`).

- [x] **Step 7: Commit the fix**

```bash
git add uipath_claude/cli/app.py
git commit -m "fix(cli): route QUESTION intents to simple_llm_answer, bypass agentic graph

- Import simple_llm_answer from query.simple_answer
- Add QUESTION routing before planning block
- Print [ANSWERING] marker for evaluation tests
- Update history and skip to next turn after answer
- Prevents planning-style responses for simple questions"
```

Expected: Clean commit with no linter errors.

---

## Task 2: Update evaluation test expectations (if needed)

**Files:**
- Modify: `docs/evaluations/test_cases.json` (if any tests expect `[PLANNING]` for `QUESTION` intents)
- Modify: `docs/evaluations/run_evaluations.py` (if parser needs to handle `[ANSWERING]` mode)

- [ ] **Step 1: Check if any evaluation tests classify as `QUESTION`**

Run:
```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
rg '"mode":\s*"' docs/evaluations/test_cases.json | rg -i question
```

Expected: If no matches, skip this task. If matches exist, proceed to Step 2.

- [ ] **Step 2: Add `answering` mode detection to `run_evaluations.py`**

In `run_evaluations.py`, find the `detect_mode` function (around line 150–200) and add:

```python
    if "[ANSWERING]" in stdout:
        return "answering"
```

Insert this check **before** the `planning_then_execution` check (so `[ANSWERING]` takes precedence).

- [ ] **Step 3: Update test cases to expect `answering` mode**

For any test with `technical.mode: "question"` or similar, change to:

```json
"technical": {
  "mode": "answering",
  "crash_not_allowed": true
}
```

- [ ] **Step 4: Run a sample evaluation test**

Pick a test ID that should be a `QUESTION` intent (e.g., `"QUEST-001"` if one exists) and run:

```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
python -u docs/evaluations/run_evaluations.py --test QUEST-001
```

Expected: Test passes with `mode: answering` detected.

- [ ] **Step 5: Commit evaluation updates**

```bash
git add docs/evaluations/run_evaluations.py docs/evaluations/test_cases.json
git commit -m "test(eval): add 'answering' mode detection for QUESTION intents

- Detect [ANSWERING] marker in stdout
- Update test expectations for QUESTION-classified tests
- Ensures evaluation harness recognizes new routing"
```

---

## Task 3: Add unit test for QUESTION routing (optional, if time permits)

**Files:**
- Modify: `tests/unit/cli/test_app.py` (if exists)
- Create: `tests/unit/cli/test_question_routing.py` (if `test_app.py` is too large)

- [ ] **Step 1: Check if `test_app.py` exists**

Run:
```powershell
Test-Path "c:\Users\DanielaRosenstein\projects\uipath-builder-agent\tests\unit\cli\test_app.py"
```

Expected: `True` or `False`. If `False`, create the file first.

- [ ] **Step 2: Write test for QUESTION routing**

Add this test to `tests/unit/cli/test_app.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner


def test_cli_chat_question_intent_uses_simple_answer():
    """QUESTION intents should call simple_llm_answer, not agentic graph."""
    runner = CliRunner()
    
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock()
        
        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            with patch(
                "uipath_claude.cli.app.simple_llm_answer",
                new=AsyncMock(return_value="project.json holds metadata for your UiPath project."),
            ) as mock_simple:
                result = runner.invoke(
                    __import__("uipath_claude.cli.app", fromlist=["main"]).main,
                    ["chat", "--no-plan"],
                    input="What is project.json?\nexit\n",
                    catch_exceptions=False,
                )
                
                assert result.exit_code == 0
                # simple_llm_answer should be called
                mock_simple.assert_called_once()
                call_kwargs = mock_simple.call_args.kwargs
                assert "What is project.json?" in call_kwargs["user_input"]
                
                # Graph should NOT be invoked for QUESTION intent
                mock_graph.ainvoke.assert_not_called()
                
                # Output should contain [ANSWERING] marker
                assert "[ANSWERING]" in result.output
```

- [ ] **Step 3: Run the test**

Run:
```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
python -m pytest tests/unit/cli/test_app.py::test_cli_chat_question_intent_uses_simple_answer -xvs
```

Expected: PASS.

- [ ] **Step 4: Run all CLI tests to ensure no regressions**

Run:
```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
python -m pytest tests/unit/cli/ -q
```

Expected: All tests pass.

- [ ] **Step 5: Commit test**

```bash
git add tests/unit/cli/test_app.py
git commit -m "test(cli): add unit test for QUESTION intent routing

- Verify simple_llm_answer is called for QUESTION intents
- Verify agentic graph is NOT invoked
- Check [ANSWERING] marker in output"
```

---

## Task 4: Update documentation

**Files:**
- Modify: `docs/evaluations/HOW_TO_RUN_TESTS.md` — Document the `[ANSWERING]` mode
- Modify: `README.md` or `docs/CLI.md` (if exists) — Document question vs build behavior

- [ ] **Step 1: Document `[ANSWERING]` mode in `HOW_TO_RUN_TESTS.md`**

Find the section about execution modes (search for `[PLANNING]` or `[EXECUTING]`) and add:

```markdown
### Execution Modes

The CLI prints markers to indicate different execution phases:

- `[ANSWERING]`: Simple Q&A mode for informational questions (no tools, no file generation)
- `[PLANNING]`: Planning phase for BUILD/AMBIGUOUS intents (if plan mode enabled)
- `[EXECUTING]`: Agentic execution phase (with tools and file generation)

**QUESTION intents** (e.g., "What is project.json?") trigger `[ANSWERING]` mode and bypass planning.

**BUILD intents** (e.g., "Create an Excel reader") trigger `[PLANNING]` (if enabled) then `[EXECUTING]`.
```

- [ ] **Step 2: Add a CLI usage example**

Add this example to `HOW_TO_RUN_TESTS.md` under "Manual Testing":

```markdown
#### Testing QUESTION Intent Routing

```powershell
python -m uipath_claude.cli.app --no-plan
```

At the prompt:
- Type: `What is project.json?`
- Expected: `[ANSWERING]` marker + simple explanation (no `[PLANNING]` or "Implementation Plan")

- Type: `Create a workflow that reads Excel`
- Expected: `[PLANNING]` + "Implementation Plan" panel (or `[EXECUTING]` if `--no-plan`)
```
\```

- [ ] **Step 3: Commit documentation**

```bash
git add docs/evaluations/HOW_TO_RUN_TESTS.md
git commit -m "docs(eval): document [ANSWERING] mode for QUESTION intents

- Explain QUESTION vs BUILD routing
- Add manual test examples
- Clarify execution mode markers"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** All requirements (QUESTION routing, simple_llm_answer integration, testing, docs) have tasks.
- [x] **Placeholder scan:** No "TBD", "TODO", or vague steps. All code blocks are complete.
- [x] **Type consistency:** `simple_llm_answer` signature matches usage (`user_input`, `history`, `model_name`, `region`, `stream`, `on_delta`). `IntentType.QUESTION` is used consistently.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-16-fix-question-intent-routing.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
