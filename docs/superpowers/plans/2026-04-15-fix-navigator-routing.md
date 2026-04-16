# Fix Navigator Agent Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Cases F, G, and H by adding a clarification gate for AMBIGUOUS intents, a simple answer path for QUESTION intents, and ensuring BUILD intents scaffold projects before tool use.

**Architecture:** Add a `clarifier.py` module that asks clarifying questions for AMBIGUOUS intents before planning. Add a `simple_answer()` function for QUESTION intents that bypasses the agentic executor and skill tools entirely. Update the chat system prompt to include project scaffolding instructions (matching the eval prompt). Modify `app.py` to route intents through these new paths before reaching the planner.

**Tech Stack:** Python 3.11+, langchain-aws (ChatBedrockConverse), pytest, unittest.mock

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `uipath_claude/query/clarifier.py` | Create | Clarification agent for AMBIGUOUS intents |
| `uipath_claude/query/simple_answer.py` | Create | Direct LLM answer for QUESTION intents |
| `uipath_claude/cli/app.py` | Modify (lines 55-85, 810-900) | Update system prompt + add routing for AMBIGUOUS and QUESTION |
| `tests/unit/query/test_clarifier.py` | Create | Unit tests for clarifier module |
| `tests/unit/query/test_simple_answer.py` | Create | Unit tests for simple_answer module |
| `tests/unit/query/test_intent_classifier.py` | Modify | Add test cases for Cases F and G |

---

## Task 1: Create clarifier module with tests

**Files:**
- Create: `uipath_claude/query/clarifier.py`
- Create: `tests/unit/query/test_clarifier.py`

- [ ] **Step 1: Write the failing test for run_clarifier_agent**

```python
# tests/unit/query/test_clarifier.py
"""Tests for clarifier module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunClarifierAgent:
    @pytest.mark.asyncio
    @patch("uipath_claude.query.clarifier.ChatBedrockConverse")
    async def test_returns_clarifying_questions(self, mock_chat_cls):
        from uipath_claude.query.clarifier import run_clarifier_agent

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "What email provider do you want to use? Do you need to read or send emails?"
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        result = await run_clarifier_agent(
            user_request="automate my email",
            model_name="test-model",
            region="us-east-1",
        )

        assert "?" in result
        assert mock_chat.ainvoke.called

    @pytest.mark.asyncio
    @patch("uipath_claude.query.clarifier.ChatBedrockConverse")
    async def test_system_prompt_forbids_code_generation(self, mock_chat_cls):
        from uipath_claude.query.clarifier import run_clarifier_agent

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "What provider?"
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        await run_clarifier_agent(
            user_request="automate my email",
            model_name="test-model",
            region="us-east-1",
        )

        call_args = mock_chat.ainvoke.call_args[0][0]
        system_msg = call_args[0]
        assert "Do NOT generate" in system_msg.content
        assert "code" in system_msg.content.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/query/test_clarifier.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'uipath_claude.query.clarifier'"

- [ ] **Step 3: Write minimal implementation**

```python
# uipath_claude/query/clarifier.py
"""Clarification agent for ambiguous user requests."""

from __future__ import annotations

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage


_CLARIFIER_SYSTEM_PROMPT = """You are a helpful assistant for UiPath automation. The user's request is ambiguous or missing critical details.

Your ONLY job is to ask 2-3 specific clarifying questions to understand:
1. What system, application, or data source they want to automate
2. What specific actions they need (read, write, send, process, etc.)
3. What inputs/outputs are expected

Rules:
- Ask questions in a numbered list format
- Be concise - no more than 3 questions
- Do NOT generate any code, XAML, implementation plans, or file contents
- Do NOT make assumptions about what the user wants
- Do NOT say "I'll create" or "I'll build" - only ask questions

Example response format:
To help you build the right automation, I have a few questions:
1. Which email provider do you use (Outlook, Gmail, etc.)?
2. Do you need to read emails, send emails, or both?
3. What should happen with the emails after processing?"""


async def run_clarifier_agent(
    user_request: str,
    *,
    model_name: str,
    region: str,
) -> str:
    """Ask clarifying questions for an ambiguous request.

    Args:
        user_request: The ambiguous user request
        model_name: Bedrock model ID
        region: AWS region

    Returns:
        String containing clarifying questions
    """
    chat = ChatBedrockConverse(
        model=model_name,
        region_name=region,
    )

    messages = [
        SystemMessage(content=_CLARIFIER_SYSTEM_PROMPT),
        HumanMessage(content=f"User request: {user_request}"),
    ]

    response = await chat.ainvoke(messages)
    return str(response.content)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/query/test_clarifier.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/query/clarifier.py tests/unit/query/test_clarifier.py
git commit -m "feat: add clarifier module for ambiguous requests"
```

---

## Task 2: Create simple_answer module with tests

**Files:**
- Create: `uipath_claude/query/simple_answer.py`
- Create: `tests/unit/query/test_simple_answer.py`

- [ ] **Step 1: Write the failing test for simple_llm_answer**

```python
# tests/unit/query/test_simple_answer.py
"""Tests for simple_answer module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSimpleLlmAnswer:
    @pytest.mark.asyncio
    @patch("uipath_claude.query.simple_answer.ChatBedrockConverse")
    async def test_returns_informational_response(self, mock_chat_cls):
        from uipath_claude.query.simple_answer import simple_llm_answer

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "A project.json file contains metadata about your UiPath project including name, dependencies, and entry points."
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        result = await simple_llm_answer(
            user_input="What is project.json?",
            history=[],
            model_name="test-model",
            region="us-east-1",
        )

        assert "project.json" in result.lower() or "metadata" in result.lower()
        assert mock_chat.ainvoke.called

    @pytest.mark.asyncio
    @patch("uipath_claude.query.simple_answer.ChatBedrockConverse")
    async def test_system_prompt_forbids_file_generation(self, mock_chat_cls):
        from uipath_claude.query.simple_answer import simple_llm_answer

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Explanation here."
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        await simple_llm_answer(
            user_input="Explain project.json",
            history=[],
            model_name="test-model",
            region="us-east-1",
        )

        call_args = mock_chat.ainvoke.call_args[0][0]
        system_msg = call_args[0]
        assert "Do NOT generate files" in system_msg.content

    @pytest.mark.asyncio
    @patch("uipath_claude.query.simple_answer.ChatBedrockConverse")
    async def test_includes_history_in_messages(self, mock_chat_cls):
        from uipath_claude.query.simple_answer import simple_llm_answer

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Answer."
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        await simple_llm_answer(
            user_input="Follow up question",
            history=history,
            model_name="test-model",
            region="us-east-1",
        )

        call_args = mock_chat.ainvoke.call_args[0][0]
        # System + 2 history + 1 current = 4 messages
        assert len(call_args) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/query/test_simple_answer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'uipath_claude.query.simple_answer'"

- [ ] **Step 3: Write minimal implementation**

```python
# uipath_claude/query/simple_answer.py
"""Simple LLM answer for informational questions (no tools)."""

from __future__ import annotations

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


_SIMPLE_ANSWER_SYSTEM_PROMPT = """You are UiPath Claude Code, an AI assistant that helps users understand UiPath automation concepts.

You are answering an INFORMATIONAL QUESTION. Your job is to explain, describe, or clarify - NOT to build anything.

Rules:
- Provide clear, helpful explanations
- Use bullet points or numbered lists when appropriate
- Do NOT generate files, code blocks, XAML, or implementation plans
- Do NOT use file markers like <<<UIPATH_FILE>>> or ```path:
- Do NOT say "I'll create" or "Let me build" - just answer the question
- If the user wants you to build something, they will ask in a follow-up message

Answer the user's question directly and informatively."""


async def simple_llm_answer(
    user_input: str,
    history: list[dict[str, str]],
    *,
    model_name: str,
    region: str,
) -> str:
    """Answer an informational question without tools or file generation.

    Args:
        user_input: The user's question
        history: Conversation history as list of {"role": ..., "content": ...}
        model_name: Bedrock model ID
        region: AWS region

    Returns:
        String containing the answer
    """
    chat = ChatBedrockConverse(
        model=model_name,
        region_name=region,
    )

    messages: list[SystemMessage | HumanMessage | AIMessage] = [
        SystemMessage(content=_SIMPLE_ANSWER_SYSTEM_PROMPT)
    ]

    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_input))

    response = await chat.ainvoke(messages)
    return str(response.content)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/query/test_simple_answer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/query/simple_answer.py tests/unit/query/test_simple_answer.py
git commit -m "feat: add simple_answer module for informational questions"
```

---

## Task 3: Add test cases for Cases F and G to intent classifier tests

**Files:**
- Modify: `tests/unit/query/test_intent_classifier.py`

- [ ] **Step 1: Write the new test cases**

```python
# Add to tests/unit/query/test_intent_classifier.py
# Insert these into the existing @pytest.mark.parametrize list

@pytest.mark.parametrize(
    "text,expected,reason_substr",
    [
        # Existing cases
        ("What is UiPath Orchestrator?", IntentType.QUESTION, "question"),
        ("How does the queue work?", IntentType.QUESTION, "question"),
        ("Create an Outlook workflow that reads email", IntentType.BUILD, "build"),
        ("Build a dispatcher", IntentType.BUILD, "build"),
        ("automate", IntentType.AMBIGUOUS, "vague"),
        ("help", IntentType.AMBIGUOUS, "vague"),
        # Case F: Ambiguous build request
        ("Automate my email.", IntentType.AMBIGUOUS, "vague"),
        ("automate my email", IntentType.AMBIGUOUS, "vague"),
        # Case G: Informational question (should NOT trigger build)
        (
            "Explain in bullet points what belongs in a minimal UiPath Studio project.json for a Windows VB workflow project, and what Main.xaml is for.",
            IntentType.QUESTION,
            "question",
        ),
        ("Explain what project.json contains", IntentType.QUESTION, "question"),
        ("What is Main.xaml for?", IntentType.QUESTION, "question"),
    ],
)
def test_classify_intent(text: str, expected: IntentType, reason_substr: str) -> None:
    intent, reason = classify_intent(text)
    assert intent == expected
    assert reason_substr in reason
```

- [ ] **Step 2: Run test to verify current behavior**

Run: `pytest tests/unit/query/test_intent_classifier.py -v`
Expected: All tests PASS (these are verifying existing behavior)

- [ ] **Step 3: Commit**

```bash
git add tests/unit/query/test_intent_classifier.py
git commit -m "test: add Cases F and G to intent classifier tests"
```

---

## Task 4: Modify app.py to route AMBIGUOUS to clarifier

**Files:**
- Modify: `uipath_claude/cli/app.py` (lines 810-900)

- [ ] **Step 1: Add import for clarifier at top of file**

Find line 35 (`from uipath_claude.query.planner import run_planner_agent`) and add after it:

```python
from uipath_claude.query.clarifier import run_clarifier_agent
```

- [ ] **Step 2: Add clarification gate before planning phase**

Find line 836 (the `if intent in (IntentType.BUILD, IntentType.AMBIGUOUS):` inside plan mode). Replace the entire block from line 836 to line 896 with:

```python
            # AMBIGUOUS: Ask clarifying questions first, don't plan yet
            if intent == IntentType.AMBIGUOUS:
                console.print("[bold yellow][CLARIFYING][/bold yellow]")
                with progress.generating("clarifying questions"):
                    clarification = asyncio.run(
                        run_clarifier_agent(
                            user_request=user_input,
                            model_name=model_name,
                            region=region,
                        )
                    )
                console.print(f"[magenta]Assistant:[/magenta] {clarification}\n")
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": clarification})
                # Store context for next turn - user's answer will provide details
                clarification_prefix = (
                    f"The user's original request was ambiguous: '{user_input}'\n"
                    f"You asked for clarification: {clarification}\n"
                    "The user's next message is their response to your questions.\n"
                )
                continue

            # BUILD: Proceed with planning phase
            if intent == IntentType.BUILD:
                plan_cancelled = False
                while True:
                    console.print("[bold cyan][PLANNING][/bold cyan]")
                    with progress.generating("implementation plan"):
                        plan_result = asyncio.run(
                            run_planner_agent(
                                user_input,
                                project_context=project_context,
                                model_name=model_name,
                                region=region,
                            )
                        )

                    from rich.markdown import Markdown
                    from rich.panel import Panel
                    console.print(Panel(Markdown(plan_result.final_response), title="Implementation Plan", border_style="cyan"))

                    console.print(
                        "[dim]Plan approval: [bold]y[/bold] = run with this plan, "
                        "[bold]n[/bold] = cancel this build, "
                        "[bold]adjust[/bold] = replan after you describe changes "
                        "(alias: [bold]edit[/bold]). Other text = feedback and replan.[/dim]"
                    )
                    while True:
                        choice_raw = Prompt.ask("Approve plan? (y/n/adjust)", default="y")
                        choice = choice_raw.strip().lower()
                        if choice in ("y", "yes"):
                            approved_plan = plan_result.final_response
                            plan_path = _save_plan_to_file(
                                session_id=chat_session_id,
                                user_request=user_input,
                                plan_content=approved_plan,
                                output_root=_get_output_root(),
                            )
                            console.print(f"[dim]Plan saved to: {plan_path}[/dim]")
                            break
                        if choice in ("n", "no"):
                            progress.info("Plan cancelled.")
                            plan_cancelled = True
                            break
                        if choice in ("adjust", "edit"):
                            feedback = Prompt.ask("What should change in the plan?").strip()
                            if not feedback:
                                console.print(
                                    "[yellow]No feedback given. Choose y, n, or adjust again "
                                    "(plan is shown above).[/yellow]"
                                )
                                continue
                            user_input = f"{user_input}\n\nFeedback on plan: {feedback}"
                            break
                        user_input = f"{user_input}\n\nFeedback on plan: {choice_raw.strip()}"
                        break

                    if plan_cancelled:
                        break
                    if approved_plan:
                        break

                if plan_cancelled:
                    continue
```

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `pytest tests/unit/cli/ tests/unit/query/ -v --tb=short`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add uipath_claude/cli/app.py
git commit -m "feat: route AMBIGUOUS intents to clarifier before planning"
```

---

## Task 5: Modify app.py to route QUESTION to simple_answer

**Files:**
- Modify: `uipath_claude/cli/app.py`

- [ ] **Step 1: Add import for simple_answer at top of file**

Find the clarifier import added in Task 4 and add after it:

```python
from uipath_claude.query.simple_answer import simple_llm_answer
```

- [ ] **Step 2: Add QUESTION routing before the planning block**

Find the line `plan_mode_enabled = os.environ.get("UIPATH_PLAN_MODE", "1")...` (around line 834). Insert BEFORE it:

```python
        # QUESTION: Simple answer path - no tools, no planning
        if intent == IntentType.QUESTION:
            with progress.generating("answer"):
                response = asyncio.run(
                    simple_llm_answer(
                        user_input=user_input,
                        history=history,
                        model_name=model_name,
                        region=region,
                    )
                )
            console.print(f"[magenta]Assistant:[/magenta] {response}\n")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})
            continue

```

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `pytest tests/unit/cli/ tests/unit/query/ -v --tb=short`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add uipath_claude/cli/app.py
git commit -m "feat: route QUESTION intents to simple_answer (bypass planning)"
```

---

## Task 6: Manual QA verification for Cases F and G

**Files:**
- Reference: `docs/MANUAL_EVAL_AND_QA.md`

- [ ] **Step 1: Set up test environment**

```powershell
cd <REPO_ROOT>\uipath-builder-agent
$env:UIPATH_AGENTIC_MODE = "1"
$env:UIPATH_DEBUG_AGENT = "1"
uipath-claude chat
```

- [ ] **Step 2: Test Case F - Ambiguous build**

Input:
```text
Automate my email.
```

Expected:
- See `[CLARIFYING]` indicator (NOT `[PLANNING]`)
- Assistant asks clarifying questions about provider, read vs send, etc.
- NO implementation plan panel
- NO file generation

- [ ] **Step 3: Test Case G - Read-only / advisory**

Start a new chat session, then input:
```text
Explain in bullet points what belongs in a minimal UiPath Studio project.json for a Windows VB workflow project, and what Main.xaml is for. Do not create or modify files on disk unless I explicitly ask you to in a follow-up message.
```

Expected:
- NO `[PLANNING]` or `[CLARIFYING]` indicator
- Direct explanatory answer with bullet points
- NO file generation markers (<<<UIPATH_FILE>>> or ```path:)
- Answer describes project.json and Main.xaml purposes

- [ ] **Step 4: Document results in session log**

Update the Pass/Fail columns in `docs/MANUAL_EVAL_AND_QA.md`:
- Case F: PASS if clarifying questions shown
- Case G: PASS if explanatory answer with no files

- [ ] **Step 5: Commit QA results**

```bash
git add docs/MANUAL_EVAL_AND_QA.md
git commit -m "docs: mark Cases F and G as PASS after routing fix"
```

---

## Task 7: Fix Case H - Add project scaffolding instruction to system prompt

**Problem:** The chat system prompt (`_UIPATH_CHAT_SYSTEM` in `app.py`) does not instruct the agent to call `ensure_project_structure` before using other tools. The eval prompt has this instruction, but the chat prompt does not. This causes Case H (Excel workflow) to fail because the agent tries to install packages or write files without a project.json.

**Files:**
- Modify: `uipath_claude/cli/app.py` (lines 55-85)

- [ ] **Step 1: Read the current system prompt**

The current `_UIPATH_CHAT_SYSTEM` at line 55-84 lacks project scaffolding instructions.

- [ ] **Step 2: Update _UIPATH_CHAT_SYSTEM to include scaffolding instruction**

Find the `_UIPATH_CHAT_SYSTEM` constant (lines 55-84) and replace it with:

```python
_UIPATH_CHAT_SYSTEM = """You are UiPath Claude Code, an agentic AI assistant with direct access to the user's local file system, UiPath CLI, and UiPath skills. You build UiPath Studio automations (workflow XAML), not WPF desktop apps, unless the user explicitly asks for WPF.

CRITICAL CAPABILITIES:
- You HAVE full capabilities to execute UiPath skills, read/write files, run CLI commands, and build automations directly on the user's machine.
- NEVER say you don't have access to tools, skills, or the local environment. You ARE an agentic assistant.
- When the user asks you to do something, DO IT using your tools (if in agentic mode) or by generating the necessary files.

IMPORTANT - Clarification Before Action:
If the user's request is ambiguous, vague, or missing critical details needed to build a correct workflow, ASK for clarification BEFORE generating any files. Examples of when to ask:
- "automate email" - Ask: What email provider? Read or send? What should happen with the emails?
- "process data" - Ask: What data source? What processing? What output?
- "click button" - Ask: Which application? What button? What should happen after?
- "integrate with X" - Ask: What specific operations? Read/write/both? What data?

Do NOT guess or make assumptions about critical workflow logic. It's better to ask one clarifying question than to generate a workflow that doesn't match the user's needs.

CRITICAL - Project Scaffolding (ALWAYS do this first for BUILD requests):
- Call ensure_project_structure early (default project_dir ".") so project.json exists before any other tool calls.
- Write workflows as Main.xaml (and supporting .xaml if needed) under that same project directory.
- After every write_file of XAML or C#, call validate_file for the same project_dir and file_path.
- Install NuGet packages with install_package AFTER ensure_project_structure but BEFORE writing XAML that uses those activities.
- When static validation is clean and the workflow is safe to run, use run_workflow to verify runtime.

If a UiPath project already exists (project.json found), do not regenerate scaffold files unless the user explicitly asks.
When the user asks for a workflow, default to writing only `.xaml` workflow files.
Do not invent or pin legacy dependency versions in `project.json`; if package changes are required, explain the `uip rpa install-or-update-packages` command instead.

When the user asks you to CREATE, WRITE, or GENERATE files, you MUST include one or more file blocks using EXACTLY this format (markers on their own lines; path uses forward slashes only):

<<<UIPATH_FILE path="Main.xaml">>>
...complete file body...
<<<END_UIPATH_FILE>>>

Put files under logical subpaths (e.g. `demo/Main.xaml`). Use only relative paths; no `..` segments.
You may instead use a markdown code fence whose first line is exactly: path: <relative/path> then the file body on following lines until the closing fence.

After the blocks you may add one short sentence summarizing what you wrote."""
```

- [ ] **Step 3: Run existing tests to verify no regression**

Run: `pytest tests/unit/cli/ -v --tb=short`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add uipath_claude/cli/app.py
git commit -m "fix: add project scaffolding instruction to chat system prompt (Case H)"
```

---

## Task 8: Manual QA verification for Case H

**Files:**
- Reference: `docs/MANUAL_EVAL_AND_QA.md`

- [ ] **Step 1: Set up test environment**

```powershell
cd <REPO_ROOT>\uipath-builder-agent
$env:UIPATH_AGENTIC_MODE = "1"
$env:UIPATH_DEBUG_AGENT = "1"
uipath-claude chat
```

- [ ] **Step 2: Test Case H - Excel path**

Input:
```text
Create a UiPath workflow that reads range A1:B10 from an Excel file named "Input.xlsx" in the project folder (assume the file will exist next to the project), writes the same data to Sheet2 starting at A1, using UiPath.Excel.Activities. Project dir ".", entry Main.xaml. After writing XAML, run validate_file. List which packages you installed.
```

Expected:
- `[PLANNING]` shows an implementation plan mentioning `ensure_project_structure`
- After approval, executor calls `ensure_project_structure` FIRST (visible in Step 1)
- Then `install_package` for Excel activities
- Then `write_file` for Main.xaml
- Then `validate_file` 
- `project.json` and `Main.xaml` exist in the session folder

- [ ] **Step 3: Verify tool call order in terminal output**

Look for this sequence in the debug output:
1. `ensure_project_structure` - creates project.json
2. `install_package` - adds UiPath.Excel.Activities
3. `write_file` - creates Main.xaml
4. `validate_file` - validates the XAML

If `install_package` or `write_file` comes BEFORE `ensure_project_structure`, the fix is not working.

- [ ] **Step 4: Document results**

Update the Pass/Fail column in `docs/MANUAL_EVAL_AND_QA.md`:
- Case H: PASS if tool order is correct and files are generated

- [ ] **Step 5: Commit QA results**

```bash
git add docs/MANUAL_EVAL_AND_QA.md
git commit -m "docs: mark Case H as PASS after scaffolding fix"
```

---

## Summary

After completing all tasks:
1. AMBIGUOUS intents ("Automate my email") will trigger the clarifier agent which asks 2-3 questions before any planning
2. QUESTION intents ("Explain what project.json is") will get a direct LLM answer without tools or planning
3. BUILD intents proceed to planning, and the executor now scaffolds projects first with `ensure_project_structure`

The routing flow becomes:

```
User Input
    |
    v
classify_intent()
    |
    +-- QUESTION --> simple_llm_answer() --> display --> done
    |
    +-- AMBIGUOUS --> run_clarifier_agent() --> display questions --> wait for user
    |                                                                      |
    |                                           (user provides details) <--+
    |                                                      |
    |                                               re-classify
    |                                                      |
    +-- BUILD --> run_planner_agent() --> plan approval --> executor
                                                              |
                                                              v
                                                    ensure_project_structure
                                                              |
                                                              v
                                                    install_package (if needed)
                                                              |
                                                              v
                                                    write_file (Main.xaml)
                                                              |
                                                              v
                                                    validate_file
```
