# Phase 2 Implementation Plan: Claude-Code UiPath Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the gap between "basic Bedrock chat" and "real Claude-Code-like UiPath agent" by implementing dynamic skill loading/execution, meaningful slash commands, bootstrap orchestration, and structured cleanup.

**Current gap summary:**
- `chat` works with real Bedrock responses.
- `/skills` is stubbed.
- `/bootstrap` command is stubbed.
- AskAI/Orchestrator tools are stubs.
- Skill discovery exists but is not integrated into chat runtime/tool routing.
- Root folder still carries non-product artifacts that should be archived/organized.

---

## Scope Decomposition

This phase is split into 4 independent subsystems:
1. **Skill Inventory + Loading**
2. **Command Runtime + Bootstrap**
3. **Tool Routing (AskAI / Orchestrator / Analyzer / SkillTool)**
4. **Repository Cleanup + Regression Protection**

Each subsystem ships with its own tests and acceptance checks.

---

## Subsystem 1: Skill Inventory + Loading

### Task 1.1: Harden skill discovery parser
**Files**
- Modify: `uipath_claude/skills/discovery.py`
- Test: `tests/unit/skills/test_discovery.py`

**Changes**
- Replace `eval()` frontmatter parsing with safe YAML parsing (`yaml.safe_load`).
- Preserve metadata fields: `name`, `description`, `triggers`, `path`, optional tags.
- Attach absolute `path` for each discovered skill.

**Tests**
- Valid frontmatter parse.
- Missing frontmatter handling.
- Invalid frontmatter handling.
- Verify no `eval` usage.

### Task 1.2: Implement layered skill registry sources
**Files**
- Modify: `uipath_claude/skills/registry.py`
- Add: `uipath_claude/skills/sources.py`
- Test: `tests/unit/skills/test_skill_registry.py`

**Source precedence**
1. Project-local: `.uipath-claude/skills/`
2. User-local: `%USERPROFILE%/.cursor/skills/`
3. Official UiPath: `skills/skills/`
4. Cato templates: `templates/**/.cursor/skills/`

**Changes**
- Centralize source building in `sources.py`.
- Keep first-source-wins dedupe.
- Add optional filtering by agent role.

**Tests**
- Multi-source dedupe order.
- Path resolution for all 4 source tiers.
- Agent filter behavior for `ba`, `sa`, `developer`, `qa`, `conversational`.

### Task 1.3: Implement real `/skills` output
**Files**
- Modify: `uipath_claude/commands/skills.py`
- Modify: `uipath_claude/cli/app.py` (inject context into registry command handlers)
- Test: `tests/unit/commands/test_skills.py`
- Test: `tests/integration/test_chat_flow.py`

**Changes**
- `/skills` lists discovered skills grouped by source and count.
- Optional `/skills <role>` to filter.
- Output includes top skill names and paths.

**Acceptance**
- No "to be implemented" text remains.

---

## Subsystem 2: Command Runtime + Bootstrap

### Task 2.1: Make `/bootstrap` execute real flow
**Files**
- Modify: `uipath_claude/commands/bootstrap.py`
- Modify: `uipath_claude/cli/app.py`
- Reuse: `uipath_claude/query/bootstrap.py`
- Test: `tests/unit/commands/test_bootstrap.py`
- Test: `tests/integration/test_bootstrap_flow.py`

**Changes**
- `/bootstrap "<request>"` runs `run_bootstrap_flow(...)`.
- Render stage-by-stage output: BA -> SA -> Dev -> QA.
- Handle runtime exceptions with actionable error text.

**Tests**
- Command parsing for `/bootstrap`.
- Success path (mock agents).
- Error path resilience.

### Task 2.2: Improve `/status`
**Files**
- Modify: `uipath_claude/commands/status.py`
- Test: `tests/unit/commands/test_status.py`

**Changes**
- Show: current model, region, project detection, skill counts, memory loaded status.

---

## Subsystem 3: Tool Routing & Relevance from Claude Code

### Task 3.1: Re-review Claude Code features and map relevance
**Files**
- Add: `docs/CLAUDE_CODE_FEATURE_RELEVANCE_MATRIX.md`

**Matrix sections**
- Keep/implement now
- Implement later
- Skip (not relevant for UiPath CLI scope)

**Candidate feature families**
- Query/tool orchestration loop
- Skills loading semantics
- Slash command ergonomics
- Hooks and memory behavior
- Output rendering patterns
- Safety/tool limits

### Task 3.2: Implement usable AskAI + Orchestrator entry points
**Files**
- Modify: `uipath_claude/tools/uipath/askai.py`
- Modify: `uipath_claude/tools/uipath/orchestrator.py`
- Add/Modify: `uipath_claude/tools/uipath/__init__.py`
- Tests: `tests/unit/tools/uipath/test_askai.py`, `tests/unit/tools/uipath/test_orchestrator.py`

**Changes**
- Add concrete adapters with explicit configuration checks.
- If backend integrations are unavailable, return precise setup guidance (not TODO strings).

### Task 3.3: Skill tool execution path in chat
**Files**
- Modify: `uipath_claude/cli/app.py`
- Modify: `uipath_claude/tools/skill_tool.py`
- Add: `uipath_claude/query/router.py`
- Tests: `tests/unit/query/test_router.py`, `tests/integration/test_chat_flow.py`

**Changes**
- Lightweight router:
  - slash command -> command handler
  - explicit skill invocation syntax -> `SkillTool`
  - everything else -> LLM response

---

## Subsystem 4: Cleanup + Guardrails

### Task 4.1: Complete repo cleanup pass
**Files**
- Modify: `.gitignore`
- Modify: `docs/CLEANUP_PLAN.md`
- Add: `archive/README.md`
- Add: `scripts/maintenance/README.md`

**Changes**
- Keep product-root minimal.
- Archive generated reports and one-off artifacts.
- Enforce single local venv convention (`.venv/`).

### Task 4.2: Add regression tests to prevent "stub regression"
**Files**
- Add: `tests/unit/test_no_stub_strings.py`

**Checks**
- Fail build if command outputs still contain:
  - "to be implemented"
  - "TODO: Implement"

### Task 4.3: Add CLI smoke script for CI/local
**Files**
- Add: `scripts/maintenance/smoke_cli.py`

**Behavior**
- Run `uipath-claude --help`
- Run scripted REPL session (`/help`, `/skills`, `exit`)
- Return non-zero on failure.

---

## Test Strategy (must pass before completion)

1. `pytest tests/unit/skills -v`
2. `pytest tests/unit/commands -v`
3. `pytest tests/unit/tools/uipath -v`
4. `pytest tests/integration/test_chat_flow.py tests/integration/test_bootstrap_flow.py -v`
5. `pytest tests/ -v`
6. REPL smoke:
   - `uipath-claude chat`
   - `/help`
   - `/skills`
   - `/bootstrap "build invoice automation"`
   - `exit`

---

## Definition of Done

- No user-facing command returns placeholder text.
- `/skills` shows real discovered skills from UiPath + Cato + local sources.
- `/bootstrap` executes and renders flow output.
- AskAI/Orchestrator tools provide concrete behavior or explicit setup guidance.
- Cleanup completed per `docs/CLEANUP_PLAN.md`.
- Full test suite passes.
