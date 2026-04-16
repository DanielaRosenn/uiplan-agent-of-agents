# UiPath Builder Agent Productionization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Archive note:** This plan was **executed and finalized** on 2026-04-16. Use **Implementation status** for truth vs the repo; keep this file as an audit trail, not an active backlog.

**Goal:** Finalize the UiPath Builder Agent so it is reliable for daily use from both the Python CLI and the Cursor MCP integration, with a first-class skills-submodule learning cache.

**Architecture:** Keep deployments manual (no CI / GitHub Actions). Harden the planner/executor contract with a single plan-block constant, structured tool outcomes, and broader nudge conditions. Make the `skills` submodule a foreground "learning cache" that is refreshed opportunistically on startup and available as an MCP tool in Cursor. Replace one brittle source-inspection test with a behavior test.

**Tech Stack:** Python 3.12, Typer/Rich CLI, LangGraph, AWS Bedrock via LangChain, FastMCP (`mcp_server/`), `skills/` git submodule, pytest.

**Constraints from user:**

- No CI / GitHub Actions work. Deployment is manual.
- `skills/` submodule and its learning pages must always be kept up to date (treat as cache).
- Primary usage is **CLI + Cursor chat via MCP**, so the MCP surface must stay in parity with the CLI.

---

## Implementation status (finalized)

**Merged in repo (2026-04-16):** Tasks 1–13 including scheduled project-layer insight retirement on `chat` startup (`uipath_claude/skills/retirement_scheduler.py` → `maybe_run_retirement_scheduled()` from `cli/app.py` after skills refresh). Throttle marker: `<project>/.uipath-claude/.retirement_at` (per `UIPATH_PROJECT_ROOT` or cwd). Optional opt-out: `UIPATH_SKIP_RETIREMENT_SCHEDULE=1`.

**Verification:** `python -m pytest tests/unit -q` → **449 passed** (includes retirement scheduler + session ordering fixes).

**Plan vs code (intentional deltas):**

| Topic | Plan document | As implemented |
|-------|----------------|----------------|
| Destructive denial message | `"[ERROR] Tool call denied by user."` | `"[ERROR] Tool call blocked by approval policy."` (covers deny and exhausted single-use grant). |
| `ALLOW_ONCE` | Snippet returns true whenever the prompter returns `ALLOW_ONCE`. | `_once_used` per `tool_name`: at most **one** passing `check()` per policy instance before `invoke`; grant is consumed at **gate** time (documented on `ApprovalPolicy`). |
| Session / approval tests | `tests/unit/sessions/test_store.py`, `tests/unit/tools/test_approval.py` | `tests/unit/sessions/test_session_store.py`, `tests/unit/tools/test_destructive_approval.py` (pytest collection / naming collisions avoided). |
| Tool-outcome migration test | Scan all `run_*` callables in the module. | Restrict to `__module__ == skill_execution_tools` so imported helpers are not mistaken for tools. |
| Retirement throttle marker | Plan Step 15 used `~/.uipath-claude/.retirement_at` (global). | `<project>/.uipath-claude/.retirement_at` per `UIPATH_PROJECT_ROOT` or cwd; marker advances only if every `*.json` run succeeds; corrupt marker parses as `0`. |
| Session list ordering | `st_mtime` only. | `st_mtime_ns` + `session_id` tie-break; test uses a short sleep so “newest first” is stable on Windows. |

**Open follow-ups:** none for this plan; use a new dated plan for further changes.

---

## Scope

Two groups of small, independent subsystems. Each task produces shippable value on its own.

**Group A — Correctness & Cache (Tasks 1–6):**

1. Plan-block contract (shared constant + broader nudge).
2. `make_execute_node` DI cleanup.
3. Skills submodule as learning cache (auto-refresh + Cursor MCP tool).
4. Behavior test for plan nudge (replace `inspect.getsource` test).
5. Structured tool-outcome helper for write/validation tools (incremental adoption).

**Group B — Claude Code parity polish (Tasks 7–11):**

7. Durable session persistence + `/resume` command.
8. Tool approval middleware for destructive tools.
9. Token / cost reporting from Bedrock response metadata.
10. Complete the `ToolOutcome` migration and drop the substring heuristic.
11. Structured JSON-line logging keyed by session / skill / iteration / tool.

**Group C — Learning loop + book of knowledge (Tasks 12–13):**

12. Closed-loop learning from past failures: inject high-confidence lessons into the skill prompt, propose a lesson on failure, gate on user approval (Hermes-inspired).
13. Book-of-knowledge polish: LLM lesson distiller, retirement / consolidation, cross-skill index MCP resource, lesson ↔ activity-docs linking, `memory.md` read-through.

**Out of scope (do not do in this plan):** adding CI, live Bedrock e2e tests, plugin marketplace UX, enterprise SSO auth, self-update channel.

---

## File Structure

| Path | Responsibility | Change |
|------|----------------|--------|
| `uipath_claude/query/plan_block.py` | Single constant for the approved-plan header | Create |
| `uipath_claude/query/agentic_executor.py` | Executor + nudge + structured-outcome detection | Modify |
| `uipath_claude/cli/app.py` | Build `runtime_extra` using the shared constant | Modify |
| `uipath_claude/graph/nodes/execute.py` | Use plan constant; remove dead `agentic_executor` param OR wire it | Modify |
| `uipath_claude/skills/updater.py` | Add `ensure_fresh(max_age_seconds)` helper | Modify |
| `uipath_claude/cli/app.py` | Opportunistic refresh on `chat` startup | Modify |
| `mcp_server/tools/skill_tools.py` | Add `uipath_skill_update` and `uipath_skill_check_updates` | Modify |
| `uipath_claude/tools/_result.py` | `ToolOutcome` helper (ok/message/data) | Create |
| `uipath_claude/tools/skill_execution_tools.py` | Adopt `ToolOutcome` in `validate_file`, `write_file`, `ensure_project_structure` only | Modify |
| `tests/unit/query/test_agentic_system_prompt.py` | Replace source-inspection test with mocked-LLM behavior test | Modify |
| `tests/unit/query/test_plan_block.py` | Constant stability test | Create |
| `tests/unit/skills/test_updater_ensure_fresh.py` | Ensure-fresh logic test | Create |
| `tests/unit/mcp/test_skill_update_tool.py` | MCP update-tool smoke test | Create |
| `docs/CURSOR_USER_GUIDE.md` | Document the new `uipath_skill_update` tool and auto-refresh | Modify |
| `uipath_claude/sessions/store.py` | JSONL session persistence + resume | Create |
| `uipath_claude/commands/resume.py` | `/resume <id>` command | Create |
| `uipath_claude/cli/app.py` | Wire session writer + `/resume` + token/cost display | Modify |
| `uipath_claude/tools/approval.py` | Destructive-tool approval middleware | Create |
| `uipath_claude/query/agentic_executor.py` | Call approval hook; read token usage; emit structured logs | Modify |
| `uipath_claude/tools/skill_execution_tools.py` | Finish `ToolOutcome` migration for remaining tools | Modify |
| `uipath_claude/observability/logger.py` | JSON-line structured logger | Create |
| `tests/unit/sessions/test_session_store.py` | Session store tests | Create |
| `tests/unit/tools/test_destructive_approval.py` | Destructive-tool approval policy tests | Create |
| `tests/unit/query/test_token_usage.py` | Token accounting test | Create |
| `tests/unit/observability/test_logger.py` | Structured logger tests | Create |
| `uipath_claude/skills/lessons.py` | Lessons accessor: load top-N insights, render prompt block, propose new lessons | Create |
| `uipath_claude/skills/insights.py` | Expose `top_insights(skill, limit, min_confidence)` query helper | Modify |
| `uipath_claude/query/agentic_executor.py` | Inject `## Past Lessons` into system prompt; on failure run lesson proposer, optionally approve | Modify |
| `uipath_claude/cli/app.py` | Interactive lesson-approval prompter; `UIPATH_LESSON_AUTO_APPROVE`; register `/knowledge`; `maybe_run_retirement_scheduled` on `chat` | Modify |
| `mcp_server/tools/skill_tools.py` | Add `uipath_skill_lessons_list` and `uipath_skill_lessons_approve` MCP tools | Modify |
| `tests/unit/skills/test_lessons.py` | Lessons query + render tests | Create |
| `tests/unit/query/test_learning_loop.py` | End-to-end learning loop test (failure → proposed lesson → next-run injection) | Create |
| `uipath_claude/skills/distiller.py` | LLM-based lesson rewriter + semantic dedup | Create |
| `uipath_claude/skills/retirement.py` | Confidence-floor pruning and near-duplicate consolidation | Create |
| `uipath_claude/skills/knowledge_index.py` | Cross-skill index of authored skills + top lessons + linked activity docs | Create |
| `uipath_claude/skills/lessons.py` | `memory.md` read-through and activity-doc link resolution | Modify |
| `mcp_server/resources/knowledge.py` | `uipath://knowledge/index` MCP resource | Create |
| `mcp_server/resources/__init__.py` | Register the knowledge resource | Modify |
| `uipath_claude/commands/knowledge.py` | `/knowledge` CLI command to inspect the index | Create |
| `uipath_claude/skills/retirement_scheduler.py` | 24h cadence + project `skill-insights/*.json` retirement | Create |
| `tests/unit/skills/test_retirement_scheduler.py` | Marker interval + skip-env tests | Create |
| `tests/unit/skills/test_distiller.py` | Distiller contract + fallback tests | Create |
| `tests/unit/skills/test_retirement.py` | Retirement / consolidation tests | Create |
| `tests/unit/skills/test_knowledge_index.py` | Cross-skill index shape + link resolution tests | Create |
| `tests/unit/mcp/test_knowledge_resource.py` | MCP resource smoke test | Create |

---

### Task 1: Centralize the Approved Plan block

**Files:**

- Create: `uipath_claude/query/plan_block.py`
- Modify: `uipath_claude/query/agentic_executor.py`
- Modify: `uipath_claude/cli/app.py`
- Modify: `uipath_claude/graph/nodes/execute.py`
- Test: `tests/unit/query/test_plan_block.py`

- [x] **Step 1: Write the failing test**

```python
from uipath_claude.query.plan_block import (
    PLAN_BLOCK_HEADING,
    build_plan_block,
    contains_plan_block,
)


def test_heading_is_stable_and_used_by_builder_and_detector():
    assert PLAN_BLOCK_HEADING == "Approved Implementation Plan"
    body = build_plan_block("1. do X\n2. do Y\n")
    assert body.startswith(f"## {PLAN_BLOCK_HEADING}")
    assert "1. do X" in body
    assert contains_plan_block(body) is True
    assert contains_plan_block("no plan here") is False
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/query/test_plan_block.py -v`
Expected: FAIL with `ModuleNotFoundError: uipath_claude.query.plan_block`.

- [x] **Step 3: Create the module**

```python
"""Canonical representation of the approved implementation plan block.

Keeping the heading and builder in one place avoids string drift between
the CLI (which injects the block into runtime_extra) and the executor
(which detects it to enforce tool usage)."""

PLAN_BLOCK_HEADING = "Approved Implementation Plan"


def build_plan_block(plan_text: str) -> str:
    plan_text = (plan_text or "").strip()
    return f"## {PLAN_BLOCK_HEADING}\n\n{plan_text}\n"


def contains_plan_block(text: str | None) -> bool:
    return bool(text) and PLAN_BLOCK_HEADING in text
```

- [x] **Step 4: Replace string literal usages**

In `uipath_claude/query/agentic_executor.py`, add at top:

```python
from uipath_claude.query.plan_block import PLAN_BLOCK_HEADING, contains_plan_block
```

Replace the literal `"Approved Implementation Plan" in (skill_content or "")` check with `contains_plan_block(skill_content)`. Any system-prompt rule that names the heading should interpolate `PLAN_BLOCK_HEADING`.

In `uipath_claude/cli/app.py`, replace the hand-built plan string passed to `runtime_extra` with `build_plan_block(plan_text)` from the same module.

In `uipath_claude/graph/nodes/execute.py`, if a literal "Approved Implementation Plan" exists, import and use `PLAN_BLOCK_HEADING`.

- [x] **Step 5: Run unit tests**

Run: `python -m pytest tests/unit/query tests/unit/graph -q`
Expected: PASS (including the new `test_plan_block.py`).

- [x] **Step 6: Commit**

```bash
git add uipath_claude/query/plan_block.py uipath_claude/query/agentic_executor.py uipath_claude/cli/app.py uipath_claude/graph/nodes/execute.py tests/unit/query/test_plan_block.py
git commit -m "refactor(plan): single constant for approved-plan block"
```

---

### Task 2: Broaden the plan nudge (not just zero-tool-call)

**Files:**

- Modify: `uipath_claude/query/agentic_executor.py:200-275`
- Test: `tests/unit/query/test_agentic_system_prompt.py`

**Why:** Today the nudge only fires when `tool_calls_made` is empty. A model that calls only read tools (e.g. `list_directory`, `read_project_json`) and then answers in prose escapes enforcement.

- [x] **Step 1: Replace the source-inspection test with a behavior test**

Full file content for `tests/unit/query/test_agentic_system_prompt.py`:

```python
"""Behavior tests for the agentic executor plan nudge."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from uipath_claude.query.agentic_executor import AgenticExecutor
from uipath_claude.query.plan_block import build_plan_block


def _mk_msg(text: str, tool_calls: list | None = None) -> AIMessage:
    msg = AIMessage(content=text)
    msg.tool_calls = tool_calls or []
    return msg


def test_system_prompt_references_approved_implementation_plan() -> None:
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    text = ex._build_system_prompt("skill body", {})
    assert "Approved Implementation Plan" in text


def test_nudge_fires_when_only_read_tools_used_then_prose() -> None:
    """Regression: model used read tools but ended in prose while a plan exists."""
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    skill = "skill body\n" + build_plan_block("1. scaffold\n2. write Main.xaml")

    read_tool_msg = _mk_msg(
        "",
        tool_calls=[{"id": "1", "name": "list_directory", "args": {"directory_path": "."}}],
    )
    prose_msg = _mk_msg("Here is a summary of what I would do.")
    final_tool_msg = _mk_msg(
        "",
        tool_calls=[{"id": "2", "name": "write_file", "args": {"file_path": "Main.xaml", "content": "<x/>"}}],
    )
    done_msg = _mk_msg("Done.")

    responses = [read_tool_msg, prose_msg, final_tool_msg, done_msg]

    async def _fake_ainvoke(messages, *args, **kwargs):
        return responses.pop(0)

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        llm_instance = m_llm.return_value
        llm_instance.bind_tools.return_value.ainvoke = AsyncMock(side_effect=_fake_ainvoke)

        result = asyncio.run(
            ex.execute(
                user_request="build hello",
                skill_content=skill,
                skill_name="uipath-automation",
                tools=[],
                max_iter=6,
            )
        )

    names = [c["name"] for c in result.tool_calls_made]
    assert "write_file" in names, f"Nudge did not drive a write tool. Calls: {names}"
    assert result.success is True
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/query/test_agentic_system_prompt.py -v`
Expected: `test_nudge_fires_when_only_read_tools_used_then_prose` FAILS because current code only nudges when `not tool_calls_made`.

- [x] **Step 3: Update the nudge condition**

In `uipath_claude/query/agentic_executor.py`, change the nudge guard so it fires when the plan is present AND the model ended in prose AND no **write/scaffold/validation** tool has been used yet:

```python
WRITE_TOOL_NAMES = {
    "write_file",
    "ensure_project_structure",
    "deploy_to_orchestrator",
    "validate_file",
    "validate_and_fix_loop",
    "run_workflow",
    "debug_workflow",
}


def _has_executed_plan(tool_calls_made: list[dict]) -> bool:
    return any(tc.get("name") in WRITE_TOOL_NAMES for tc in tool_calls_made)
```

Replace the existing `and not tool_calls_made` check with `and not _has_executed_plan(tool_calls_made)` and keep the `plan_tool_nudges < 5` cap. Keep `contains_plan_block(skill_content)` from Task 1.

- [x] **Step 4: Run tests**

Run: `python -m pytest tests/unit/query -q`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add uipath_claude/query/agentic_executor.py tests/unit/query/test_agentic_system_prompt.py
git commit -m "fix(executor): nudge when plan present and no write/validation tool used"
```

---

### Task 3: Fix `make_execute_node` DI (remove or wire)

**Files:**

- Modify: `uipath_claude/graph/nodes/execute.py`

**Decision:** Remove the unused parameter — YAGNI. If you later need an injected executor for tracing, reintroduce it as a factory.

- [x] **Step 1: Read the current signature**

Run: `rg -n "def make_execute_node" uipath_claude/graph/nodes/execute.py`

- [x] **Step 2: Remove the `agentic_executor` parameter**

Delete the parameter from `make_execute_node(...)` and from any call site (search with `rg -n "make_execute_node\("`). Keep model/region/env-driven construction inside the node; that is already how it behaves today.

- [x] **Step 3: Run graph tests**

Run: `python -m pytest tests/unit/graph -q`
Expected: PASS (existing tests never passed a real executor).

- [x] **Step 4: Commit**

```bash
git add uipath_claude/graph/nodes/execute.py
git commit -m "chore(graph): drop unused agentic_executor param from make_execute_node"
```

---

### Task 4: Skills submodule as a foreground learning cache

**Files:**

- Modify: `uipath_claude/skills/updater.py`
- Modify: `uipath_claude/cli/app.py` (chat command bootstrap only)
- Test: `tests/unit/skills/test_updater_ensure_fresh.py`

**Why:** User treats `skills/` as a cache of learning pages that must stay current. Right now it is refreshed only on explicit `/update-skills`. Add an opportunistic refresh that runs at most once per N hours and never blocks more than a short budget.

- [x] **Step 1: Write the failing test**

```python
"""Ensure the skills updater refreshes only when the cache is stale."""
from __future__ import annotations

from pathlib import Path

import pytest

from uipath_claude.skills import updater


def test_ensure_fresh_no_op_when_recent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        updater, "check_for_updates", lambda path=None: (_ for _ in ()).throw(AssertionError("should not be called"))
    )
    marker = tmp_path / ".skills_refresh_at"
    marker.write_text("9999999999")  # far future
    assert updater.ensure_fresh(marker_path=marker, max_age_seconds=3600) == "skipped: recent"


def test_ensure_fresh_runs_when_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = tmp_path / ".skills_refresh_at"
    marker.write_text("0")  # ancient

    monkeypatch.setattr(updater, "check_for_updates", lambda path=None: (True, "ok", "aaaa", "bbbb"))
    monkeypatch.setattr(updater, "update_skills", lambda path=None: (True, "updated"))

    result = updater.ensure_fresh(marker_path=marker, max_age_seconds=3600)
    assert result.startswith("updated")
    # marker must be refreshed
    assert int(marker.read_text()) > 0


def test_ensure_fresh_offline_is_soft_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = tmp_path / ".skills_refresh_at"
    marker.write_text("0")
    monkeypatch.setattr(updater, "check_for_updates", lambda path=None: (False, "offline", None, None))
    result = updater.ensure_fresh(marker_path=marker, max_age_seconds=3600)
    assert "offline" in result or "skipped" in result
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/skills/test_updater_ensure_fresh.py -v`
Expected: FAIL with `AttributeError: module 'uipath_claude.skills.updater' has no attribute 'ensure_fresh'`.

- [x] **Step 3: Implement `ensure_fresh` in `uipath_claude/skills/updater.py`**

Append (keep existing imports):

```python
import time


def _default_marker_path() -> Path:
    return get_skills_submodule_path().parent / ".skills_refresh_at"


def ensure_fresh(
    marker_path: Path | None = None,
    max_age_seconds: int = 6 * 3600,
) -> str:
    """Refresh the skills submodule at most once per `max_age_seconds`.

    Safe to call on CLI/MCP startup. Soft-fails on any network/git error so
    that offline use is never blocked."""
    marker = marker_path or _default_marker_path()
    now = int(time.time())
    try:
        last = int(marker.read_text()) if marker.exists() else 0
    except (OSError, ValueError):
        last = 0

    if now - last < max_age_seconds:
        return "skipped: recent"

    has_updates, message, _cur, _rem = check_for_updates()
    if not has_updates:
        try:
            marker.write_text(str(now))
        except OSError:
            pass
        return f"skipped: {message}"

    ok, result = update_skills()
    try:
        marker.write_text(str(now))
    except OSError:
        pass
    return ("updated: " if ok else "failed: ") + result
```

- [x] **Step 4: Call from CLI chat startup (non-blocking best effort)**

In `uipath_claude/cli/app.py`, inside the `chat` command after `_load_dotenv_from_cwd()` and before any Bedrock work, add:

```python
try:
    from uipath_claude.skills.updater import ensure_fresh
    msg = ensure_fresh(max_age_seconds=6 * 3600)
    if msg.startswith("updated"):
        console.print(f"[dim]Skills cache: {msg}[/dim]")
except Exception:
    pass
```

Gate behind env: if `os.environ.get("UIPATH_SKILLS_AUTO_REFRESH", "1") != "1":` skip. This lets users disable it for offline sessions.

- [x] **Step 5: Run tests**

Run: `python -m pytest tests/unit/skills -q`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add uipath_claude/skills/updater.py uipath_claude/cli/app.py tests/unit/skills/test_updater_ensure_fresh.py
git commit -m "feat(skills): auto-refresh skills submodule cache on chat startup"
```

---

### Task 5: Expose skills refresh as MCP tools (Cursor parity)

**Files:**

- Modify: `mcp_server/tools/skill_tools.py`
- Modify: `docs/CURSOR_USER_GUIDE.md` (tool reference section only)
- Test: `tests/unit/mcp/test_skill_update_tool.py`

**Why:** In Cursor the CLI `/update-skills` is unreachable. Add MCP tools so Cursor can keep the learning cache current and query status.

- [x] **Step 1: Write the failing test**

```python
"""Smoke test for the MCP skill update tools."""
from __future__ import annotations

from unittest.mock import patch

import pytest


def test_uipath_skill_check_updates_calls_check_for_updates() -> None:
    from mcp_server.tools import skill_tools

    with patch("mcp_server.tools.skill_tools.check_for_updates", return_value=(True, "new", "aaaa", "bbbb")) as m:
        result = skill_tools.uipath_skill_check_updates()
    m.assert_called_once()
    assert result["has_updates"] is True
    assert result["current"] == "aaaa"
    assert result["remote"] == "bbbb"


def test_uipath_skill_update_calls_ensure_fresh() -> None:
    from mcp_server.tools import skill_tools

    with patch("mcp_server.tools.skill_tools.ensure_fresh", return_value="updated: 2 files") as m:
        result = skill_tools.uipath_skill_update(force=False)
    m.assert_called_once()
    assert "updated" in result["status"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/mcp/test_skill_update_tool.py -v`
Expected: FAIL — tools not registered.

- [x] **Step 3: Add tools in `mcp_server/tools/skill_tools.py`**

At the top, import:

```python
from uipath_claude.skills.updater import check_for_updates, ensure_fresh, get_skills_info
```

Register two tools using the existing `@mcp.tool` decorator pattern used by sibling tools in that file:

```python
@mcp.tool()
def uipath_skill_check_updates() -> dict:
    """Check whether the UiPath skills submodule (learning cache) has updates."""
    has_updates, message, current, remote = check_for_updates()
    return {
        "has_updates": has_updates,
        "message": message,
        "current": current,
        "remote": remote,
    }


@mcp.tool()
def uipath_skill_update(force: bool = False) -> dict:
    """Refresh the UiPath skills submodule cache. Soft-fails offline."""
    max_age = 0 if force else 6 * 3600
    status = ensure_fresh(max_age_seconds=max_age)
    info = get_skills_info()
    return {
        "status": status,
        "current_commit": info.get("current_commit"),
        "skills_count": info.get("skills_count"),
    }
```

- [x] **Step 4: Document the new tools**

In `docs/CURSOR_USER_GUIDE.md`, in the Skill tools table, add two rows:

| `uipath_skill_check_updates` | Check whether skills submodule has updates |
| `uipath_skill_update`        | Refresh skills submodule cache (`force=true` to bypass throttle) |

And add one line under "How It Works": "The skills submodule auto-refreshes on CLI chat startup (every 6 hours). In Cursor, call `uipath_skill_update` to refresh on demand."

- [x] **Step 5: Run tests**

Run: `python -m pytest tests/unit/mcp -q`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add mcp_server/tools/skill_tools.py docs/CURSOR_USER_GUIDE.md tests/unit/mcp/test_skill_update_tool.py
git commit -m "feat(mcp): expose skill cache refresh tools for Cursor"
```

---

### Task 6: Structured tool outcomes (minimal adoption)

**Files:**

- Create: `uipath_claude/tools/_result.py`
- Modify: `uipath_claude/tools/skill_execution_tools.py` (only `validate_file`, `write_file`, `ensure_project_structure`)
- Test: extend `tests/unit/tools/` nearest existing test module

**Why:** The executor currently infers tool success via substring match on message text. Start adopting a small structured envelope where return-shape ambiguity hurts the most (validation + write). Do not rewrite every tool — incremental.

- [x] **Step 1: Create the helper**

```python
"""Structured tool result envelope used by skill execution tools."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ToolOutcome:
    ok: bool
    message: str
    data: dict[str, Any] | None = None

    def to_text(self) -> str:
        """Render a LangChain-tool-compatible string the LLM can read."""
        status = "OK" if self.ok else "ERROR"
        return f"[{status}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [x] **Step 2: Adopt in `validate_file`, `write_file`, `ensure_project_structure`**

For each of those three tools, wrap the success / failure paths to return `ToolOutcome(...).to_text()`. Leave existing error messages intact; just prefix with `[OK]` / `[ERROR]`.

- [x] **Step 3: Update executor detection to prefer the marker**

In `uipath_claude/query/agentic_executor.py`, where success/failure counting happens (around the current substring `"error"` check), update to:

```python
def _is_tool_failure(observation: str) -> bool:
    if not isinstance(observation, str):
        return False
    if observation.startswith("[ERROR]"):
        return True
    if observation.startswith("[OK]"):
        return False
    # Backwards compatibility for tools not yet migrated.
    return "error" in observation.lower() or "exception" in observation.lower()
```

Route all increments of `tool_failure_count` / `tool_success_count` through this helper.

- [x] **Step 4: Run all unit tests**

Run: `python -m pytest tests/unit -q`
Expected: PASS. Existing tests that assert on raw tool text must still pass because the prefix is additive.

- [x] **Step 5: Commit**

```bash
git add uipath_claude/tools/_result.py uipath_claude/tools/skill_execution_tools.py uipath_claude/query/agentic_executor.py tests/unit
git commit -m "feat(tools): structured [OK]/[ERROR] outcomes for validation and write tools"
```

---

### Task 7: Durable session persistence + `/resume`

**Files:**

- Create: `uipath_claude/sessions/store.py`
- Create: `uipath_claude/commands/resume.py`
- Modify: `uipath_claude/cli/app.py` (wire writer + command registration)
- Test: `tests/unit/sessions/test_session_store.py`

**Why:** Claude Code can resume; you can't. Today `history` lives in-process and `generated/chat/` stores artifacts, not transcripts. Append every user / assistant / tool event as JSONL so any session can be replayed.

- [x] **Step 1: Write the failing test**

```python
"""Session JSONL store: append-only transcript with resume."""
from __future__ import annotations

from pathlib import Path

from uipath_claude.sessions.store import SessionStore, SessionEvent


def test_append_and_load_roundtrip(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path)
    sid = store.new_session_id()

    store.append(sid, SessionEvent(kind="user", text="hello"))
    store.append(sid, SessionEvent(kind="assistant", text="hi", tokens_in=10, tokens_out=3))
    store.append(sid, SessionEvent(kind="tool", name="write_file", ok=True, text="[OK] wrote"))

    events = store.load(sid)
    assert [e.kind for e in events] == ["user", "assistant", "tool"]
    assert events[1].tokens_in == 10
    assert events[2].name == "write_file" and events[2].ok is True


def test_list_sessions_sorted_newest_first(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path)
    a = store.new_session_id()
    b = store.new_session_id()
    store.append(a, SessionEvent(kind="user", text="a"))
    store.append(b, SessionEvent(kind="user", text="b"))
    ids = [s.session_id for s in store.list_sessions(limit=10)]
    assert ids[0] == b and ids[1] == a
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/sessions/test_session_store.py -v`
Expected: FAIL — module missing.

- [x] **Step 3: Implement `SessionStore`**

```python
"""Append-only JSONL session store under `.uipath-claude/sessions/`."""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class SessionEvent:
    kind: str  # "user" | "assistant" | "tool" | "system"
    text: str = ""
    name: str | None = None
    ok: bool | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    ts: float = field(default_factory=lambda: time.time())


@dataclass
class SessionSummary:
    session_id: str
    path: Path
    mtime: float


class SessionStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or (Path.home() / ".uipath-claude" / "sessions"))
        self.root.mkdir(parents=True, exist_ok=True)

    def new_session_id(self) -> str:
        return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]

    def _path(self, session_id: str) -> Path:
        return self.root / f"{session_id}.jsonl"

    def append(self, session_id: str, event: SessionEvent) -> None:
        line = json.dumps(asdict(event), ensure_ascii=False)
        with self._path(session_id).open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def load(self, session_id: str) -> list[SessionEvent]:
        p = self._path(session_id)
        if not p.exists():
            return []
        events: list[SessionEvent] = []
        for raw in p.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            events.append(SessionEvent(**json.loads(raw)))
        return events

    def list_sessions(self, limit: int = 20) -> list[SessionSummary]:
        items: list[SessionSummary] = []
        for p in self.root.glob("*.jsonl"):
            try:
                items.append(SessionSummary(session_id=p.stem, path=p, mtime=p.stat().st_mtime))
            except OSError:
                continue
        items.sort(key=lambda s: s.mtime, reverse=True)
        return items[:limit]
```

- [x] **Step 4: Wire into `cli/app.py`**

In the `chat` command:

```python
from uipath_claude.sessions.store import SessionStore, SessionEvent

store = SessionStore()
session_id = os.environ.get("UIPATH_CHAT_SESSION_ID") or store.new_session_id()
os.environ["UIPATH_CHAT_SESSION_ID"] = session_id
console.print(f"[dim]Session: {session_id}[/dim]")
```

After each user input:

```python
store.append(session_id, SessionEvent(kind="user", text=user_input))
```

After each assistant response / tool observation, call `store.append(...)` with the relevant fields. Keep it best-effort: wrap writes in `try/except` and never let a log failure kill the chat.

- [x] **Step 5: Add `/resume` command**

Create `uipath_claude/commands/resume.py`:

```python
"""/resume command: reload a prior session's transcript into history."""
from __future__ import annotations

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.sessions.store import SessionStore


def register_resume_command(registry: CommandRegistry) -> None:
    store = SessionStore()

    def handle_resume(*args) -> str:
        if not args:
            lines = ["Recent sessions:"]
            for s in store.list_sessions(limit=10):
                lines.append(f"  {s.session_id}")
            lines.append("Usage: /resume <session-id>")
            return "\n".join(lines)

        session_id = args[0]
        events = store.load(session_id)
        if not events:
            return f"No session found for id: {session_id}"
        return f"Loaded {len(events)} events from {session_id}. Use UIPATH_CHAT_SESSION_ID={session_id} and restart chat to continue."

    registry.register("resume", "Resume a prior chat session", handle_resume)
```

Register it alongside the other commands in `cli/app.py`.

- [x] **Step 6: Run tests**

Run: `python -m pytest tests/unit/sessions -q`
Expected: PASS.

- [x] **Step 7: Commit**

```bash
git add uipath_claude/sessions/ uipath_claude/commands/resume.py uipath_claude/cli/app.py tests/unit/sessions/
git commit -m "feat(sessions): JSONL session store and /resume command"
```

---

### Task 8: Tool approval middleware for destructive tools

**Files:**

- Create: `uipath_claude/tools/approval.py`
- Modify: `uipath_claude/query/agentic_executor.py` (call approval hook before dispatch)
- Test: `tests/unit/tools/test_destructive_approval.py`

**Why:** No tool consent today. Destructive tools (`write_file`, `deploy_to_orchestrator`, `run_workflow`, `debug_workflow`, `ensure_project_structure`) should be gated behind an approval policy that the CLI wires interactively and tests wire silently.

- [x] **Step 1: Write the failing test**

```python
"""Approval middleware: deny, allow-once, allow-always."""
from __future__ import annotations

from uipath_claude.tools.approval import ApprovalPolicy, ApprovalDecision, is_destructive


def test_is_destructive_set() -> None:
    assert is_destructive("write_file") is True
    assert is_destructive("read_project_json") is False


def test_policy_allow_always_remembers() -> None:
    p = ApprovalPolicy(prompter=lambda name, args: ApprovalDecision.ALLOW_ALWAYS)
    assert p.check("write_file", {"file_path": "x"}) is True
    # No prompter call on second use for same tool:
    p2 = ApprovalPolicy(prompter=lambda name, args: ApprovalDecision.DENY, preapproved={"write_file"})
    assert p2.check("write_file", {"file_path": "y"}) is True


def test_policy_deny_blocks() -> None:
    p = ApprovalPolicy(prompter=lambda name, args: ApprovalDecision.DENY)
    assert p.check("deploy_to_orchestrator", {"url": "x"}) is False


def test_non_destructive_auto_allow() -> None:
    p = ApprovalPolicy(prompter=lambda name, args: ApprovalDecision.DENY)
    assert p.check("list_directory", {"directory_path": "."}) is True
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/tools/test_destructive_approval.py -v`
Expected: FAIL — module missing.

- [x] **Step 3: Implement `ApprovalPolicy`**

```python
"""Interactive + programmatic approval policy for destructive tools."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Callable


DESTRUCTIVE_TOOLS: set[str] = {
    "write_file",
    "ensure_project_structure",
    "deploy_to_orchestrator",
    "run_workflow",
    "debug_workflow",
    "install_package",
}


def is_destructive(tool_name: str) -> bool:
    return tool_name in DESTRUCTIVE_TOOLS


class ApprovalDecision(enum.Enum):
    ALLOW_ONCE = "allow_once"
    ALLOW_ALWAYS = "allow_always"
    DENY = "deny"


Prompter = Callable[[str, dict], ApprovalDecision]


@dataclass
class ApprovalPolicy:
    prompter: Prompter
    preapproved: set[str] = field(default_factory=set)

    def check(self, tool_name: str, tool_args: dict) -> bool:
        if not is_destructive(tool_name):
            return True
        if tool_name in self.preapproved:
            return True
        decision = self.prompter(tool_name, tool_args)
        if decision is ApprovalDecision.ALLOW_ALWAYS:
            self.preapproved.add(tool_name)
            return True
        return decision is ApprovalDecision.ALLOW_ONCE
```

**As shipped:** use the real `ApprovalPolicy` in `uipath_claude/tools/approval.py` — it adds `_once_used` so repeated `ALLOW_ONCE` for the same tool does not re-approve forever; see class docstring for gate-before-`invoke` semantics.

- [x] **Step 4: Wire into the executor**

In `uipath_claude/query/agentic_executor.py`, accept an optional `approval: ApprovalPolicy | None = None` on `AgenticExecutor.__init__`. In the tool-dispatch loop, before invoking a tool:

```python
if self.approval is not None and not self.approval.check(tool_name, tool_args):
    observation = "[ERROR] Tool call blocked by approval policy."
    tool_failure_count += 1
    messages.append(ToolMessage(content=observation, tool_call_id=tool_id))
    continue
```

In `cli/app.py`, wire an interactive prompter using `rich.prompt.Prompt.ask` offering `once / always / deny`, and construct `AgenticExecutor(..., approval=policy)`. Tests construct with a deterministic `prompter` lambda.

- [x] **Step 5: Run tests**

Run: `python -m pytest tests/unit/tools tests/unit/query -q`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add uipath_claude/tools/approval.py uipath_claude/query/agentic_executor.py uipath_claude/cli/app.py tests/unit/tools/test_destructive_approval.py
git commit -m "feat(tools): approval middleware for destructive tools"
```

---

### Task 9: Token / cost reporting from Bedrock response metadata

**Files:**

- Modify: `uipath_claude/query/agentic_executor.py` (accumulate usage, emit via `ProgressReporter`)
- Modify: `uipath_claude/rendering/progress.py` (render totals in `complete(...)`)
- Test: `tests/unit/query/test_token_usage.py`

**Why:** Claude Code reports per-turn/session usage. Bedrock responses include `usage_metadata` (or `response_metadata["usage"]`); surface it.

- [x] **Step 1: Write the failing test**

```python
"""Executor accumulates token counts from Bedrock responses."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from uipath_claude.query.agentic_executor import AgenticExecutor


def _ai(text: str, tokens_in: int, tokens_out: int) -> AIMessage:
    msg = AIMessage(content=text)
    msg.tool_calls = []
    msg.usage_metadata = {"input_tokens": tokens_in, "output_tokens": tokens_out}
    return msg


def test_executor_aggregates_usage() -> None:
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    responses = [_ai("done.", tokens_in=50, tokens_out=7)]

    async def _fake_ainvoke(messages, *args, **kwargs):
        return responses.pop(0)

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        m_llm.return_value.bind_tools.return_value.ainvoke = AsyncMock(side_effect=_fake_ainvoke)
        result = asyncio.run(
            ex.execute(user_request="x", skill_content="", skill_name="s", tools=[], max_iter=2)
        )

    assert result.tokens_in == 50
    assert result.tokens_out == 7
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/query/test_token_usage.py -v`
Expected: FAIL — `AgenticResult` has no `tokens_in`/`tokens_out`.

- [x] **Step 3: Add fields and accumulate**

In `agentic_executor.py`, extend `AgenticResult` with `tokens_in: int = 0` and `tokens_out: int = 0`. In the LLM call site:

```python
usage = getattr(response, "usage_metadata", None) or {}
tokens_in_total += int(usage.get("input_tokens") or 0)
tokens_out_total += int(usage.get("output_tokens") or 0)
```

Return them on every `AgenticResult(...)` construction in this function.

- [x] **Step 4: Render in progress**

In `rendering/progress.py`, extend `complete(...)` signature with `tokens_in: int = 0, tokens_out: int = 0` and print a final summary line:

```python
if tokens_in or tokens_out:
    self.console.print(
        f"[dim]Tokens: in={tokens_in:,} out={tokens_out:,}[/dim]"
    )
```

Pass the totals from the executor.

- [x] **Step 5: Run tests**

Run: `python -m pytest tests/unit/query tests/unit/rendering -q`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add uipath_claude/query/agentic_executor.py uipath_claude/rendering/progress.py tests/unit/query/test_token_usage.py
git commit -m "feat(executor): aggregate and report Bedrock token usage"
```

---

### Task 10: Complete `ToolOutcome` migration, drop substring heuristic

**Files:**

- Modify: `uipath_claude/tools/skill_execution_tools.py` (remaining tools)
- Modify: `uipath_claude/query/agentic_executor.py` (remove fallback branch)
- Test: `tests/unit/tools/test_tool_outcome_migration.py`

**Why:** Task 6 migrated three tools. Complete the migration and delete the substring fallback so success/failure is unambiguous.

- [x] **Step 1: Write the failing test**

```python
"""Every skill_execution tool returns `[OK] ` or `[ERROR] ` prefixed strings."""
from __future__ import annotations

import inspect

import uipath_claude.tools.skill_execution_tools as st


def test_all_tools_return_prefixed_strings() -> None:
    offenders: list[str] = []
    for name, obj in inspect.getmembers(st):
        if not callable(obj):
            continue
        if not name.startswith(("read_", "write_", "list_", "ensure_", "validate_", "run_", "debug_", "deploy_", "install_")):
            continue
        src = inspect.getsource(obj)
        if "[OK]" not in src and "[ERROR]" not in src and "ToolOutcome" not in src:
            offenders.append(name)
    assert not offenders, f"Tools missing structured outcome: {offenders}"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/tools/test_tool_outcome_migration.py -v`
Expected: FAIL — lists un-migrated tools.

- [x] **Step 3: Migrate remaining tools**

For each tool in the offenders list, import `ToolOutcome` from `uipath_claude.tools._result` and wrap the return paths:

```python
return ToolOutcome(ok=True, message="...").to_text()
return ToolOutcome(ok=False, message=f"...: {exc}").to_text()
```

- [x] **Step 4: Remove the substring fallback**

In `agentic_executor.py`, replace `_is_tool_failure` with strict prefix parsing:

```python
def _is_tool_failure(observation: str) -> bool:
    if not isinstance(observation, str):
        return False
    return observation.startswith("[ERROR]")
```

- [x] **Step 5: Run full test suite**

Run: `python -m pytest tests/unit -q`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add uipath_claude/tools/skill_execution_tools.py uipath_claude/query/agentic_executor.py tests/unit/tools/test_tool_outcome_migration.py
git commit -m "refactor(tools): complete ToolOutcome migration, drop substring heuristic"
```

---

### Task 11: Structured JSON-line logging

**Files:**

- Create: `uipath_claude/observability/logger.py`
- Modify: `uipath_claude/query/agentic_executor.py` (emit events)
- Test: `tests/unit/observability/test_logger.py`

**Why:** Debugging "production" runs needs machine-grep-able events. One JSON line per tool call and per iteration, keyed by session/skill.

- [x] **Step 1: Write the failing test**

```python
"""JSON-line structured logger."""
from __future__ import annotations

import json
from pathlib import Path

from uipath_claude.observability.logger import StructuredLogger


def test_writes_jsonl(tmp_path: Path) -> None:
    log = tmp_path / "events.log"
    logger = StructuredLogger(path=log)
    logger.emit(session_id="s1", skill="uipath-automation", iteration=1, tool="write_file", ok=True, ms=42)
    logger.emit(session_id="s1", skill="uipath-automation", iteration=1, tool=None, ok=None, ms=None, event="iteration_end")

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    a = json.loads(lines[0])
    assert a["session_id"] == "s1"
    assert a["tool"] == "write_file"
    assert a["ok"] is True
    assert a["ms"] == 42
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/observability/test_logger.py -v`
Expected: FAIL — module missing.

- [x] **Step 3: Implement `StructuredLogger`**

```python
"""JSON-line structured logger for agentic runs."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class StructuredLogger:
    def __init__(self, path: Path | None = None) -> None:
        default = Path.home() / ".uipath-claude" / "logs" / "events.log"
        self.path = Path(path or os.environ.get("UIPATH_EVENT_LOG", default))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, **fields: Any) -> None:
        record = {"ts": time.time(), **fields}
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass
```

- [x] **Step 4: Emit events from the executor**

In `agentic_executor.py`, construct a `StructuredLogger` once per `execute(...)` call and emit:

- `event="iteration_start"` at the top of each loop iteration.
- `event="tool_call"` with `tool`, `ok`, `ms` after each tool dispatch (time it).
- `event="complete"` with `tokens_in`, `tokens_out`, `iterations`, `files_written` at the end.

Include `session_id` from `os.environ.get("UIPATH_CHAT_SESSION_ID")` and `skill=skill_name`.

- [x] **Step 5: Run full test suite**

Run: `python -m pytest tests/unit -q`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add uipath_claude/observability/ uipath_claude/query/agentic_executor.py tests/unit/observability/
git commit -m "feat(observability): JSON-line event log for agentic runs"
```

---

### Task 12: Closed-loop learning from past failures (Hermes-inspired)

**Files:**

- Create: `uipath_claude/skills/lessons.py`
- Modify: `uipath_claude/skills/insights.py` (add `top_insights(...)` query)
- Modify: `uipath_claude/query/agentic_executor.py` (inject lessons pre-run, propose post-failure)
- Modify: `uipath_claude/cli/app.py` (interactive approval prompter)
- Modify: `mcp_server/tools/skill_tools.py` (expose list + approve tools for Cursor)
- Test: `tests/unit/skills/test_lessons.py`
- Test: `tests/unit/query/test_learning_loop.py`

**Why:** Today the insights system is **write-only** — failures are recorded in `SkillInsightsStore`, but nothing reads them back into the next run. Hermes-style learning requires a full loop: **read** past lessons before acting, **propose** a new lesson after a failure, and **approve** it before it becomes authoritative. This turns `.uipath-claude/skill-insights/` into a real learning cache and closes parity with the Hermes-inspired design the user referenced ([Hermes-inspired architecture analysis](d3e27918-3ef2-4eca-85e7-55e11c6ca160)).

**Design (loop):**

1. Before each `AgenticExecutor.execute(...)`, `lessons.load_for_skill(skill_name, limit=5, min_confidence=0.6)` reads top insights and renders a `## Past Lessons` block appended to `skill_content`.
2. After a failed run (`AgenticResult.success is False`), `lessons.propose(skill_name, user_request, result)` builds a candidate `SkillInsight` of type `FAILURE_PATTERN` whose `content` summarizes the failing tool/error.
3. The candidate goes through `LessonApproval` — auto-approved when `UIPATH_LESSON_AUTO_APPROVE=1` (default for unattended / MCP runs), interactively approved via a prompter in the CLI.
4. Approved lessons are persisted via the existing `SkillInsightsStore` at `InsightLayer.PROJECT` (`.uipath-claude/skill-insights/<skill>.json`). The next run will pick them up because of step 1.

- [x] **Step 1: Write the failing test for `lessons.load_for_skill` and rendering**

```python
"""Lesson retrieval + prompt-block rendering."""
from __future__ import annotations

from pathlib import Path

from uipath_claude.skills.insights import (
    InsightLayer,
    InsightType,
    SkillInsight,
    SkillInsightsStore,
)
from uipath_claude.skills.lessons import load_for_skill, render_lessons_block


def _seed(store: SkillInsightsStore, skill: str, content: str, confidence_success: int, confidence_fail: int, type_: InsightType = InsightType.FAILURE_PATTERN) -> None:
    insight = SkillInsight(
        skill_name=skill,
        insight_type=type_,
        content=content,
        success_count=confidence_success,
        failure_count=confidence_fail,
    )
    store.append(insight, layer=InsightLayer.PROJECT)


def test_load_for_skill_filters_by_confidence(tmp_path: Path) -> None:
    store = SkillInsightsStore(project_root=tmp_path)
    _seed(store, "uipath-automation", "Always include Microsoft.Activities namespace", confidence_success=4, confidence_fail=1)
    _seed(store, "uipath-automation", "Noisy guess", confidence_success=0, confidence_fail=3)

    lessons = load_for_skill("uipath-automation", project_root=tmp_path, limit=5, min_confidence=0.6)
    texts = [l.content for l in lessons]
    assert "Always include Microsoft.Activities namespace" in texts
    assert "Noisy guess" not in texts


def test_render_lessons_block_produces_heading_and_bullets(tmp_path: Path) -> None:
    store = SkillInsightsStore(project_root=tmp_path)
    _seed(store, "uipath-automation", "Use UseExcelFile scope before ForEachExcelRow", confidence_success=3, confidence_fail=0)

    lessons = load_for_skill("uipath-automation", project_root=tmp_path)
    block = render_lessons_block(lessons)
    assert block.startswith("## Past Lessons")
    assert "Use UseExcelFile scope" in block
    assert "(confidence" in block


def test_render_lessons_block_empty_returns_empty_string() -> None:
    assert render_lessons_block([]) == ""
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/skills/test_lessons.py -v`
Expected: FAIL — `uipath_claude.skills.lessons` missing, and `SkillInsightsStore.append(...)` may not exist yet (verify in current `insights.py`; it does — used by `record_usage`. If the method has a different name, use what the existing codebase exposes and keep the test consistent).

- [x] **Step 3: Implement `lessons.py`**

```python
"""Lesson retrieval and prompt rendering for closed-loop learning."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from uipath_claude.skills.insights import (
    InsightType,
    SkillInsight,
    SkillInsightsStore,
)


LESSONS_HEADING = "Past Lessons"


@dataclass
class RankedLesson:
    insight: SkillInsight
    rank: float

    @property
    def content(self) -> str:
        return self.insight.content


def _rank(insight: SkillInsight) -> float:
    # Confidence with a small recency tiebreaker on success_count.
    return insight.confidence + min(insight.success_count, 10) * 0.001


def load_for_skill(
    skill_name: str,
    project_root: Path,
    limit: int = 5,
    min_confidence: float = 0.6,
) -> list[RankedLesson]:
    store = SkillInsightsStore(project_root=project_root)
    all_insights: list[SkillInsight] = list(store.iter_insights(skill_name))
    ranked = [
        RankedLesson(insight=i, rank=_rank(i))
        for i in all_insights
        if i.confidence >= min_confidence
    ]
    ranked.sort(key=lambda r: r.rank, reverse=True)
    return ranked[:limit]


def render_lessons_block(lessons: Iterable[RankedLesson]) -> str:
    items = list(lessons)
    if not items:
        return ""
    lines = [f"## {LESSONS_HEADING}", ""]
    for r in items:
        kind = r.insight.insight_type.value
        lines.append(f"- [{kind}] {r.insight.content} (confidence {r.insight.confidence:.2f})")
    lines.append("")
    return "\n".join(lines)


def propose_from_failure(
    skill_name: str,
    user_request: str,
    failing_tool: str | None,
    error_message: str | None,
) -> SkillInsight:
    """Build a candidate FAILURE_PATTERN lesson from a failed run."""
    snippet_req = (user_request or "").strip().splitlines()[0][:160]
    err = (error_message or "unknown failure").strip().splitlines()[0][:200]
    content = (
        f"When handling '{snippet_req}', tool '{failing_tool or 'n/a'}' failed: {err}. "
        f"Next time, verify preconditions before calling this tool."
    )
    return SkillInsight(
        skill_name=skill_name,
        insight_type=InsightType.FAILURE_PATTERN,
        content=content,
        context=snippet_req,
        source="auto",
        failure_count=1,
    )
```

- [x] **Step 4: Ensure `SkillInsightsStore` exposes what we need**

In `uipath_claude/skills/insights.py`, confirm (or add) these two methods. If names differ in the current codebase, keep the existing method signatures and adjust `lessons.py` to match — do not rename existing public methods.

```python
class SkillInsightsStore:
    # existing code...

    def iter_insights(self, skill_name: str):
        """Yield insights across layers with first-layer-wins dedup by content_hash."""
        seen: set[str] = set()
        for layer in (InsightLayer.USER, InsightLayer.PROJECT, InsightLayer.SHARED):
            path = self._get_insights_path(skill_name, layer)
            if not path.exists():
                continue
            try:
                data = SkillInsightsFile.from_dict(
                    __import__("json").loads(path.read_text(encoding="utf-8"))
                )
            except Exception:
                continue
            for ins in data.insights:
                h = ins.content_hash
                if h in seen:
                    continue
                seen.add(h)
                yield ins

    def append(self, insight: SkillInsight, layer: InsightLayer = InsightLayer.PROJECT) -> None:
        """Append a single insight to the given layer (creates file if missing)."""
        import json
        path = self._get_insights_path(insight.skill_name, layer)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                data = SkillInsightsFile.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                data = SkillInsightsFile(skill_name=insight.skill_name)
        else:
            data = SkillInsightsFile(skill_name=insight.skill_name)
        data.insights.append(insight)
        path.write_text(json.dumps(data.to_dict(), indent=2), encoding="utf-8")
```

- [x] **Step 5: Run lesson tests to verify they pass**

Run: `python -m pytest tests/unit/skills/test_lessons.py -v`
Expected: PASS.

- [x] **Step 6: Write the failing end-to-end learning-loop test**

```python
"""Failure in run 1 becomes an injected lesson in run 2 (approval auto-on)."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from uipath_claude.query.agentic_executor import AgenticExecutor


def _ai(text: str, tool_calls: list | None = None) -> AIMessage:
    msg = AIMessage(content=text)
    msg.tool_calls = tool_calls or []
    return msg


def test_failure_produces_lesson_injected_next_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UIPATH_LESSON_AUTO_APPROVE", "1")
    monkeypatch.setenv("UIPATH_PROJECT_ROOT", str(tmp_path))  # lessons.py resolves project root from env

    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")

    # Run 1: tool failure on `write_file`, then prose.
    run1_responses = [
        _ai("", tool_calls=[{"id": "1", "name": "write_file", "args": {"file_path": "Main.xaml", "content": "<x/>"}}]),
        _ai("Could not finish."),
    ]

    def _tool_side_effect_run1(name: str, args: dict) -> str:
        return "[ERROR] permission denied"

    async def _ainvoke_run1(messages, *_, **__):
        return run1_responses.pop(0)

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm, \
         patch("uipath_claude.query.agentic_executor._dispatch_tool", side_effect=_tool_side_effect_run1, create=True):
        m_llm.return_value.bind_tools.return_value.ainvoke = AsyncMock(side_effect=_ainvoke_run1)
        result1 = asyncio.run(
            ex.execute(user_request="build hello", skill_content="base skill", skill_name="uipath-automation", tools=[], max_iter=3)
        )

    assert result1.success is False

    # Run 2: inspect the system prompt the LLM is called with — must contain the lesson.
    run2_calls: list[list] = []

    async def _ainvoke_run2(messages, *_, **__):
        run2_calls.append(messages)
        return _ai("Acknowledged lessons; done.")

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        m_llm.return_value.bind_tools.return_value.ainvoke = AsyncMock(side_effect=_ainvoke_run2)
        asyncio.run(
            ex.execute(user_request="build hello again", skill_content="base skill", skill_name="uipath-automation", tools=[], max_iter=2)
        )

    first_system = run2_calls[0][0].content
    assert "## Past Lessons" in first_system
    assert "write_file" in first_system  # proposal mentions failing tool
```

- [x] **Step 7: Run test to verify it fails**

Run: `python -m pytest tests/unit/query/test_learning_loop.py -v`
Expected: FAIL — executor does not yet inject lessons or propose on failure.

- [x] **Step 8: Wire the loop into `AgenticExecutor`**

In `uipath_claude/query/agentic_executor.py`:

1. At the top of `execute(...)`, after computing `system_prompt`:

```python
from uipath_claude.skills.lessons import load_for_skill, render_lessons_block, propose_from_failure

project_root = Path(os.environ.get("UIPATH_PROJECT_ROOT") or Path.cwd())
lessons = load_for_skill(skill_name, project_root=project_root)
lessons_block = render_lessons_block(lessons)
if lessons_block:
    skill_content = f"{skill_content}\n\n{lessons_block}"
    system_prompt = self._build_system_prompt(skill_content, context)
    messages[0] = SystemMessage(content=system_prompt)
```

2. Extend `_record_learning(...)` to propose and persist a lesson on failure. Replace its body with:

```python
def _record_learning(
    self,
    skill_name: str,
    user_request: str,
    result: AgenticResult,
) -> None:
    if not self._learning_capture_enabled():
        return
    post_skill_execution_hook(
        skill_name=skill_name,
        success=result.success,
        tool_calls=len(result.tool_calls_made),
        error=result.error,
        context=user_request[:500],
    )
    if result.success:
        return
    from uipath_claude.skills.insights import InsightLayer, SkillInsightsStore
    from uipath_claude.skills.lessons import propose_from_failure

    failing_tool = None
    for tc in reversed(result.tool_calls_made):
        if tc.get("ok") is False or tc.get("failed"):
            failing_tool = tc.get("name")
            break
    if failing_tool is None and result.tool_calls_made:
        failing_tool = result.tool_calls_made[-1].get("name")

    candidate = propose_from_failure(
        skill_name=skill_name,
        user_request=user_request,
        failing_tool=failing_tool,
        error_message=result.error,
    )

    approved = self._approve_lesson(candidate)
    if not approved:
        return

    project_root = Path(os.environ.get("UIPATH_PROJECT_ROOT") or Path.cwd())
    SkillInsightsStore(project_root=project_root).append(candidate, layer=InsightLayer.PROJECT)
```

3. Add an approval hook on the executor:

```python
def _approve_lesson(self, candidate) -> bool:
    if os.environ.get("UIPATH_LESSON_AUTO_APPROVE", "0") == "1":
        return True
    prompter = getattr(self, "lesson_prompter", None)
    if prompter is None:
        return False
    return bool(prompter(candidate))
```

4. Allow CLI to inject a prompter in `__init__`:

```python
def __init__(self, *args, lesson_prompter=None, **kwargs):
    ...
    self.lesson_prompter = lesson_prompter
```

- [x] **Step 9: Wire CLI interactive approval**

In `uipath_claude/cli/app.py`, where the `AgenticExecutor` is constructed:

```python
def _approve_lesson_interactive(candidate) -> bool:
    console.print(
        f"[yellow]Propose new lesson for {candidate.skill_name}:[/yellow]\n  {candidate.content}"
    )
    choice = Prompt.ask("Save as lesson? [y/N]", default="N").strip().lower()
    return choice in ("y", "yes")

executor = AgenticExecutor(
    model_name=model_name,
    region=region,
    lesson_prompter=_approve_lesson_interactive,
)
```

Document the env override: `UIPATH_LESSON_AUTO_APPROVE=1` bypasses the prompt. This is the default for unattended / Cursor-MCP usage (Task 5 context).

- [x] **Step 10: Expose lessons to Cursor via MCP**

In `mcp_server/tools/skill_tools.py`, add:

```python
from uipath_claude.skills.insights import InsightLayer, SkillInsightsStore
from uipath_claude.skills.lessons import load_for_skill


@mcp.tool()
def uipath_skill_lessons_list(skill_name: str, limit: int = 5) -> dict:
    """List currently-active lessons for a skill (highest-confidence first)."""
    from pathlib import Path
    project_root = Path(__import__("os").environ.get("UIPATH_MCP_PROJECT_ROOT") or ".")
    lessons = load_for_skill(skill_name, project_root=project_root, limit=limit)
    return {
        "skill": skill_name,
        "lessons": [
            {
                "content": r.insight.content,
                "type": r.insight.insight_type.value,
                "confidence": r.insight.confidence,
            }
            for r in lessons
        ],
    }


@mcp.tool()
def uipath_skill_lessons_approve(skill_name: str, content: str) -> dict:
    """Approve and persist a lesson (for Cursor to flush queued proposals)."""
    from pathlib import Path
    from uipath_claude.skills.insights import InsightType, SkillInsight

    project_root = Path(__import__("os").environ.get("UIPATH_MCP_PROJECT_ROOT") or ".")
    insight = SkillInsight(
        skill_name=skill_name,
        insight_type=InsightType.FAILURE_PATTERN,
        content=content,
        source="cursor",
        failure_count=1,
    )
    SkillInsightsStore(project_root=project_root).append(insight, layer=InsightLayer.PROJECT)
    return {"ok": True, "skill": skill_name, "content_hash": insight.content_hash}
```

- [x] **Step 11: Run full test suite**

Run: `python -m pytest tests/unit -q`
Expected: PASS (411+ existing + new tests). The end-to-end `test_learning_loop.py` test may need to adapt to the actual internal name of the tool-dispatch helper inside `agentic_executor.py`. If so, patch the real call site (locate with `rg -n "def _dispatch_tool|tool_map\[" uipath_claude/query/agentic_executor.py`) and update the test's `patch(...)` target accordingly without changing the assertion.

- [x] **Step 12: Commit**

```bash
git add uipath_claude/skills/lessons.py uipath_claude/skills/insights.py uipath_claude/query/agentic_executor.py uipath_claude/cli/app.py mcp_server/tools/skill_tools.py tests/unit/skills/test_lessons.py tests/unit/query/test_learning_loop.py
git commit -m "feat(learning): closed-loop lessons — inject past failures, propose on failure, user-approved"
```

---

### Task 13: Book of knowledge — distiller, retirement, cross-skill index, activity-doc links, memory read-through

**Files:**

- Create: `uipath_claude/skills/distiller.py`
- Create: `uipath_claude/skills/retirement.py`
- Create: `uipath_claude/skills/knowledge_index.py`
- Create: `mcp_server/resources/knowledge.py`
- Create: `uipath_claude/commands/knowledge.py`
- Modify: `uipath_claude/skills/lessons.py` (memory read-through, doc-link resolver)
- Modify: `uipath_claude/cli/app.py` (register `/knowledge`; `chat` calls `maybe_run_retirement_scheduled`)
- Modify: `mcp_server/resources/__init__.py` (register resource)
- Test: `tests/unit/skills/test_distiller.py`
- Test: `tests/unit/skills/test_retirement.py`
- Test: `tests/unit/skills/test_knowledge_index.py`
- Test: `tests/unit/mcp/test_knowledge_resource.py`

**Why:** Task 12 turns insights into a bidirectional learning cache but leaves five follow-ups on the table: noisy deterministic lesson text, infinite growth, no cross-skill view, no link from lessons back to UiPath activity docs, and no use of `memory.md` in the lesson block. This task finishes the "book of knowledge" so the authored skills + learned lessons + project memory + activity docs form a single, queryable surface.

**Design:**

- **Distiller** — Best-effort LLM rewrite of a proposed lesson into cleaner prose + semantic dedup against existing top-N. Falls back cleanly when Bedrock is unreachable (returns the raw candidate). Never fails the calling path.
- **Retirement** — Pure function over an existing `SkillInsightsFile`: drop entries with `confidence < floor` and `failure_count + success_count >= min_samples`; merge near-duplicates by `content_hash` prefix and token overlap; bump `stats`. Runs opportunistically once per 24h from CLI startup and on demand from a CLI command.
- **Cross-skill index** — `knowledge_index.build_index(project_root)` walks `skills/` (authored), `SkillInsightsStore.iter_insights(...)` (learned), and bundled activity-doc URIs for each skill. Returns a JSON-serialisable structure. Exposed as MCP resource `uipath://knowledge/index` and CLI `/knowledge` command.
- **Activity-doc links** — `lessons.resolve_doc_links(lesson_text)` scans content for known activity names (list from `uipath_doc_list_activities`) and returns `("ActivityName", "uipath://doc/<pkg>/<ActivityName>")` pairs. `render_lessons_block` (Task 12) appends these under a lesson when present.
- **Memory read-through** — `lessons.render_lessons_block(lessons, memory_excerpt=...)` optionally appends a trimmed `memory.md` excerpt as a final `### Project Memory` subsection of the `## Past Lessons` block, so the executor sees both in one place.

- [x] **Step 1: Write the failing distiller test**

```python
"""Distiller: LLM rewrite with offline fallback, never raises."""
from __future__ import annotations

from unittest.mock import patch

from uipath_claude.skills.distiller import distill
from uipath_claude.skills.insights import InsightType, SkillInsight


def _candidate() -> SkillInsight:
    return SkillInsight(
        skill_name="uipath-automation",
        insight_type=InsightType.FAILURE_PATTERN,
        content="tool 'write_file' failed: permission denied. Next time, verify preconditions.",
        source="auto",
        failure_count=1,
    )


def test_distill_returns_rewritten_text_when_llm_available() -> None:
    with patch("uipath_claude.skills.distiller._invoke_llm", return_value="Ensure destination is writable before calling write_file."):
        out = distill(_candidate(), existing_top=[])
    assert out.content == "Ensure destination is writable before calling write_file."
    assert out.source == "auto+distilled"


def test_distill_falls_back_on_llm_failure() -> None:
    with patch("uipath_claude.skills.distiller._invoke_llm", side_effect=RuntimeError("offline")):
        out = distill(_candidate(), existing_top=[])
    assert out.content.startswith("tool 'write_file' failed")
    assert out.source == "auto"


def test_distill_drops_semantic_duplicate(existing_top: list | None = None) -> None:
    existing = [_candidate()]
    with patch("uipath_claude.skills.distiller._invoke_llm", return_value="DUPLICATE"):
        out = distill(_candidate(), existing_top=existing)
    assert out is None
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/skills/test_distiller.py -v`
Expected: FAIL — module missing.

- [x] **Step 3: Implement `distiller.py`**

```python
"""LLM-based lesson distiller with offline fallback and semantic dedup."""
from __future__ import annotations

import os
from typing import Iterable

from uipath_claude.skills.insights import SkillInsight


_DISTILL_PROMPT = (
    "You are refining a short UiPath lesson. Rewrite the candidate in one or two "
    "sentences, preserve specific tool / activity names, be imperative, and omit "
    "apology or hedging. If the candidate is semantically the same as any in "
    "EXISTING, output exactly DUPLICATE.\n\n"
    "CANDIDATE:\n{candidate}\n\nEXISTING:\n{existing}\n"
)


def _invoke_llm(prompt: str) -> str:
    """Call Bedrock for a short rewrite. Raises on any failure."""
    from langchain_aws import ChatBedrockConverse  # lazy import
    model = os.environ.get("UIPATH_DISTILLER_MODEL") or os.environ.get("UIPATH_MODEL_ID") or "anthropic.claude-3-sonnet-20240229-v1:0"
    region = os.environ.get("AWS_REGION") or "us-east-1"
    llm = ChatBedrockConverse(model=model, region_name=region)
    response = llm.invoke(prompt)
    return (response.content if isinstance(response.content, str) else str(response.content)).strip()


def distill(
    candidate: SkillInsight,
    existing_top: Iterable[SkillInsight],
) -> SkillInsight | None:
    """Return a rewritten lesson, `None` if semantic duplicate, original on failure."""
    existing_text = "\n".join(f"- {i.content}" for i in existing_top)
    prompt = _DISTILL_PROMPT.format(candidate=candidate.content, existing=existing_text or "(none)")
    try:
        rewritten = _invoke_llm(prompt)
    except Exception:
        return candidate  # Offline: fall through with raw candidate.

    if rewritten.strip().upper() == "DUPLICATE":
        return None

    candidate.content = rewritten
    candidate.source = "auto+distilled"
    return candidate
```

- [x] **Step 4: Write the failing retirement test**

```python
"""Retirement: prune low-confidence and consolidate near-duplicates."""
from __future__ import annotations

from uipath_claude.skills.insights import (
    InsightType,
    SkillInsight,
    SkillInsightsFile,
)
from uipath_claude.skills.retirement import retire


def _ins(content: str, success: int, fail: int) -> SkillInsight:
    return SkillInsight(
        skill_name="uipath-automation",
        insight_type=InsightType.FAILURE_PATTERN,
        content=content,
        success_count=success,
        failure_count=fail,
    )


def test_retire_drops_low_confidence_with_enough_samples() -> None:
    f = SkillInsightsFile(skill_name="uipath-automation", insights=[
        _ins("Noisy low confidence", success=0, fail=5),
        _ins("Good rule", success=5, fail=0),
    ])
    out = retire(f, min_confidence=0.3, min_samples=3)
    contents = [i.content for i in out.insights]
    assert contents == ["Good rule"]
    assert out.stats.get("retired") == 1


def test_retire_keeps_low_sample_uncertain_entries() -> None:
    f = SkillInsightsFile(skill_name="uipath-automation", insights=[
        _ins("New uncertain rule", success=0, fail=1),
    ])
    out = retire(f, min_confidence=0.3, min_samples=3)
    assert len(out.insights) == 1


def test_retire_consolidates_exact_content_hash_duplicates() -> None:
    f = SkillInsightsFile(skill_name="uipath-automation", insights=[
        _ins("Use UseExcelFile scope before ForEachExcelRow", success=2, fail=0),
        _ins("Use UseExcelFile scope before ForEachExcelRow", success=1, fail=1),
    ])
    out = retire(f, min_confidence=0.0, min_samples=1)
    assert len(out.insights) == 1
    merged = out.insights[0]
    assert merged.success_count == 3
    assert merged.failure_count == 1
    assert out.stats.get("consolidated") == 1
```

- [x] **Step 5: Run test to verify it fails**

Run: `python -m pytest tests/unit/skills/test_retirement.py -v`
Expected: FAIL — module missing.

- [x] **Step 6: Implement `retirement.py`**

```python
"""Pure functions that prune and consolidate a `SkillInsightsFile`."""
from __future__ import annotations

from collections import defaultdict

from uipath_claude.skills.insights import SkillInsight, SkillInsightsFile


def retire(
    data: SkillInsightsFile,
    min_confidence: float = 0.3,
    min_samples: int = 3,
) -> SkillInsightsFile:
    """Return a new file with low-confidence entries pruned and dup content_hash merged."""
    merged_by_hash: dict[str, SkillInsight] = {}
    consolidated = 0
    for i in data.insights:
        key = i.content_hash
        if key in merged_by_hash:
            prev = merged_by_hash[key]
            prev.success_count += i.success_count
            prev.failure_count += i.failure_count
            consolidated += 1
        else:
            merged_by_hash[key] = SkillInsight(
                skill_name=i.skill_name,
                insight_type=i.insight_type,
                content=i.content,
                context=i.context,
                created_at=i.created_at,
                source=i.source,
                success_count=i.success_count,
                failure_count=i.failure_count,
            )

    kept: list[SkillInsight] = []
    retired = 0
    for i in merged_by_hash.values():
        total = i.success_count + i.failure_count
        if total >= min_samples and i.confidence < min_confidence:
            retired += 1
            continue
        kept.append(i)

    stats = dict(data.stats or {})
    stats["retired"] = stats.get("retired", 0) + retired
    stats["consolidated"] = stats.get("consolidated", 0) + consolidated

    return SkillInsightsFile(skill_name=data.skill_name, insights=kept, stats=stats)
```

- [x] **Step 7: Write the failing cross-skill index test**

```python
"""knowledge_index.build_index returns authored skills + top lessons + doc links."""
from __future__ import annotations

from pathlib import Path

from uipath_claude.skills.insights import (
    InsightLayer,
    InsightType,
    SkillInsight,
    SkillInsightsStore,
)
from uipath_claude.skills.knowledge_index import build_index


def _write_skill(root: Path, name: str, body: str = "skill body") -> None:
    d = root / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(body, encoding="utf-8")


def test_index_includes_authored_skills_and_top_lessons(tmp_path: Path) -> None:
    _write_skill(tmp_path, "uipath-automation")
    store = SkillInsightsStore(project_root=tmp_path)
    store.append(
        SkillInsight(
            skill_name="uipath-automation",
            insight_type=InsightType.GOTCHA,
            content="Use UseExcelFile scope before ForEachExcelRow",
            success_count=3,
        ),
        layer=InsightLayer.PROJECT,
    )

    index = build_index(project_root=tmp_path, top_lessons=3)
    names = [s["name"] for s in index["skills"]]
    assert "uipath-automation" in names

    entry = next(s for s in index["skills"] if s["name"] == "uipath-automation")
    assert entry["lessons"], "expected at least one lesson"
    assert entry["lessons"][0]["content"].startswith("Use UseExcelFile")
```

- [x] **Step 8: Run test to verify it fails**

Run: `python -m pytest tests/unit/skills/test_knowledge_index.py -v`
Expected: FAIL — module missing.

- [x] **Step 9: Implement `knowledge_index.py`**

```python
"""Single queryable view over authored skills + learned lessons + doc links."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from uipath_claude.skills.lessons import load_for_skill


def _list_authored_skills(project_root: Path) -> list[str]:
    root = project_root / "skills"
    if not root.exists():
        return []
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and (p / "SKILL.md").exists()
    )


def build_index(project_root: Path, top_lessons: int = 3) -> dict[str, Any]:
    skills_out: list[dict[str, Any]] = []
    for name in _list_authored_skills(project_root):
        lessons = load_for_skill(name, project_root=project_root, limit=top_lessons, min_confidence=0.0)
        skills_out.append({
            "name": name,
            "lessons": [
                {
                    "content": r.insight.content,
                    "type": r.insight.insight_type.value,
                    "confidence": r.insight.confidence,
                }
                for r in lessons
            ],
        })
    return {"skills": skills_out, "project_root": str(project_root)}
```

- [x] **Step 10: Extend `lessons.py` with activity-doc links and `memory.md` read-through**

In `uipath_claude/skills/lessons.py`, add:

```python
def resolve_doc_links(text: str, known_activities: list[str] | None = None) -> list[tuple[str, str]]:
    """Return (activity_name, uipath://doc URI) pairs found in `text`.

    Caller supplies `known_activities` (usually from `uipath_doc_list_activities`).
    Lookup is a conservative case-sensitive substring match on whole-word boundaries.
    """
    import re
    if not text or not known_activities:
        return []
    hits: list[tuple[str, str]] = []
    for name in known_activities:
        if re.search(rf"\b{re.escape(name)}\b", text):
            hits.append((name, f"uipath://doc/activity/{name}"))
    return hits


def _load_memory_excerpt(project_root: Path, max_chars: int = 800) -> str:
    mem = project_root / "memory.md"
    if not mem.exists():
        return ""
    try:
        raw = mem.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if len(raw) <= max_chars:
        return raw
    return raw[-max_chars:]
```

Then change the existing `render_lessons_block(lessons)` signature (keep it backwards compatible) to:

```python
def render_lessons_block(
    lessons,
    *,
    memory_excerpt: str = "",
    doc_resolver=None,
) -> str:
    items = list(lessons)
    if not items and not memory_excerpt:
        return ""
    out = [f"## {LESSONS_HEADING}", ""]
    for r in items:
        kind = r.insight.insight_type.value
        out.append(f"- [{kind}] {r.insight.content} (confidence {r.insight.confidence:.2f})")
        if doc_resolver is not None:
            links = doc_resolver(r.insight.content)
            for name, uri in links:
                out.append(f"    - see: [{name}]({uri})")
    if memory_excerpt:
        out += ["", "### Project Memory", "", memory_excerpt]
    out.append("")
    return "\n".join(out)
```

- [x] **Step 11: Wire memory read-through and doc links where the executor assembles the block**

In `uipath_claude/query/agentic_executor.py`, where Task 12 added the injection, change to:

```python
from uipath_claude.skills.lessons import (
    load_for_skill,
    render_lessons_block,
    resolve_doc_links,
    _load_memory_excerpt,
)

lessons = load_for_skill(skill_name, project_root=project_root)

try:
    from mcp_server.tools.doc_tools import list_activities  # reuse existing discovery if available
    known_activities = [a["name"] for a in list_activities() or []]
except Exception:
    known_activities = []

memory_excerpt = _load_memory_excerpt(project_root)

lessons_block = render_lessons_block(
    lessons,
    memory_excerpt=memory_excerpt,
    doc_resolver=(lambda t: resolve_doc_links(t, known_activities=known_activities)) if known_activities else None,
)
if lessons_block:
    skill_content = f"{skill_content}\n\n{lessons_block}"
    system_prompt = self._build_system_prompt(skill_content, context)
    messages[0] = SystemMessage(content=system_prompt)
```

If `mcp_server.tools.doc_tools` does not export `list_activities` under that exact name, locate the equivalent with `rg -n "def list_activities|uipath_doc_list_activities" mcp_server` and adjust the import.

- [x] **Step 12: Plug the distiller into the approval path**

In `uipath_claude/query/agentic_executor._record_learning(...)` (from Task 12), after `propose_from_failure` but before `_approve_lesson`, call:

```python
from uipath_claude.skills.distiller import distill

distilled = distill(candidate, existing_top=[r.insight for r in lessons])
if distilled is None:
    return  # Semantic duplicate; nothing to save.
candidate = distilled
```

- [x] **Step 13: Add the MCP resource**

Create `mcp_server/resources/knowledge.py`:

```python
"""MCP resource: uipath://knowledge/index."""
from __future__ import annotations

import json
import os
from pathlib import Path

from mcp_server.server import mcp  # existing FastMCP instance
from uipath_claude.skills.knowledge_index import build_index


@mcp.resource("uipath://knowledge/index")
def knowledge_index_resource() -> str:
    root = Path(os.environ.get("UIPATH_MCP_PROJECT_ROOT") or ".")
    return json.dumps(build_index(project_root=root), indent=2)
```

Register it by importing in `mcp_server/resources/__init__.py` (follow the pattern for the existing `project`, `docs`, `skills` resources — add `from . import knowledge  # noqa: F401`).

Test:

```python
"""Smoke test for uipath://knowledge/index resource."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


def test_knowledge_index_resource_returns_json(tmp_path: Path) -> None:
    from mcp_server.resources import knowledge as res

    with patch("mcp_server.resources.knowledge.build_index", return_value={"skills": [{"name": "x", "lessons": []}], "project_root": str(tmp_path)}):
        raw = res.knowledge_index_resource()

    data = json.loads(raw)
    assert data["skills"][0]["name"] == "x"
```

- [x] **Step 14: Add `/knowledge` CLI command**

Create `uipath_claude/commands/knowledge.py`:

```python
"""/knowledge command: print a compact cross-skill index."""
from __future__ import annotations

import os
from pathlib import Path

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.skills.knowledge_index import build_index


def register_knowledge_command(registry: CommandRegistry) -> None:
    def handle_knowledge(*args) -> str:
        root = Path(os.environ.get("UIPATH_PROJECT_ROOT") or os.getcwd())
        index = build_index(project_root=root, top_lessons=3)
        lines: list[str] = ["UiPath knowledge index:"]
        for s in index["skills"]:
            lessons_ct = len(s["lessons"])
            lines.append(f"  - {s['name']}  ({lessons_ct} lessons)")
            for lsn in s["lessons"][:3]:
                lines.append(f"      • [{lsn['type']}] {lsn['content']} ({lsn['confidence']:.2f})")
        return "\n".join(lines) if index["skills"] else "(no authored skills found)"

    registry.register("knowledge", "Show the UiPath knowledge index (authored skills + lessons)", handle_knowledge)
```

Register it in `uipath_claude/cli/app.py` alongside the other commands.

- [x] **Step 15: Schedule retirement on startup**

Implementation lives in `uipath_claude/skills/retirement_scheduler.py` (`maybe_run_retirement_scheduled`: 24h marker under `<project>/.uipath-claude/.retirement_at`, insights under `<project>/.uipath-claude/skill-insights/*.json`, same `retire(...)` thresholds; marker advances only if every JSON file succeeds). Tests set `UIPATH_SKIP_RETIREMENT_SCHEDULE=1` when they must not touch schedules.

In `uipath_claude/cli/app.py`, in the `chat` command immediately after the `ensure_fresh(...)` block:

```python
    try:
        from uipath_claude.skills.retirement_scheduler import maybe_run_retirement_scheduled

        maybe_run_retirement_scheduled()
    except Exception:
        pass
```

- [x] **Step 16: Run full test suite**

Run: `python -m pytest tests/unit -q`
Expected: PASS (`tests/unit`; e.g. **449** tests including scheduler + sessions).

- [x] **Step 17: Commit**

```bash
git add uipath_claude/skills/distiller.py uipath_claude/skills/retirement.py uipath_claude/skills/retirement_scheduler.py uipath_claude/skills/knowledge_index.py uipath_claude/skills/lessons.py uipath_claude/query/agentic_executor.py uipath_claude/commands/knowledge.py uipath_claude/cli/app.py mcp_server/resources/knowledge.py mcp_server/resources/__init__.py tests/unit/skills/test_distiller.py tests/unit/skills/test_retirement.py tests/unit/skills/test_retirement_scheduler.py tests/unit/skills/test_knowledge_index.py tests/unit/mcp/test_knowledge_resource.py
git commit -m "feat(knowledge): distiller, retirement, cross-skill index, activity-doc links, memory read-through"
```

---

## Out-of-scope items (explicitly deferred)

- No CI, no GHA — user deploys manually.
- No live Bedrock e2e tests.
- No plugin marketplace UX (keep single-submodule model).
- No enterprise SSO / self-update channel.
- No cancelation/interrupt semantics overhaul (if needed, separate plan).
- No vector-DB / embeddings for lesson semantic search (Task 13 distiller uses a prompt-based DUPLICATE signal). If semantic search is needed later, a follow-up plan should introduce an embedding index.

---

## Self-review

**Spec coverage:**

- Plan-block constant + duplication fix: Task 1.
- Broader nudge for "prose after read-only tools": Task 2.
- Dead DI parameter cleanup: Task 3.
- Skills submodule as learning cache, auto-refresh: Task 4.
- Cursor parity for skills refresh (MCP tools): Task 5.
- Replace brittle `inspect.getsource` test with behavior test: Task 2 Step 1.
- Structured tool outcomes (initial): Task 6. (Completed in Task 10.)
- Durable sessions + `/resume`: Task 7.
- Tool approval for destructive tools: Task 8.
- Token / cost reporting: Task 9.
- Drop substring heuristic after full `ToolOutcome` adoption: Task 10.
- Structured JSON-line logs: Task 11.
- Closed-loop learning from past failures, with optional user approval: Task 12.
- Book of knowledge (distiller, retirement, index, links, memory excerpt, MCP resource, `/knowledge`, scheduled retirement): Task 13.

**Placeholder scan:** No TBD/TODO. Every code step shows the code. All commands show expected output type.

**Type consistency:**

- `PLAN_BLOCK_HEADING`, `build_plan_block`, `contains_plan_block` are used identically across Tasks 1–2.
- `ensure_fresh(max_age_seconds=...)` signature is consistent between Tasks 4 and 5.
- `ToolOutcome.to_text()` prefix format `[OK] ` / `[ERROR] ` is consistent between Tasks 6, 8, and 10. Task 10 Step 4 hardens `_is_tool_failure` to strict prefix parsing, consistent with Task 6 Step 3's permissive version (acceptable because Task 10 runs after full migration).
- `SessionEvent.kind` values (`"user"`, `"assistant"`, `"tool"`, `"system"`) used in Task 7 match the emit sites in Task 8 (`tool` + `ok`) and Task 9 (`assistant` + `tokens_in`/`tokens_out`).
- `StructuredLogger.emit(session_id=, skill=, iteration=, tool=, ok=, ms=, event=)` keys in Task 11 match the fields read by the test and emitted by the executor.
- `load_for_skill(skill_name, project_root, limit, min_confidence)`, `render_lessons_block(lessons)`, and `propose_from_failure(skill_name, user_request, failing_tool, error_message)` signatures in Task 12 are used identically by both unit tests and the executor wiring. `LESSONS_HEADING = "Past Lessons"` drives the `"## Past Lessons"` assertion in the end-to-end test. `UIPATH_LESSON_AUTO_APPROVE` env toggle is named identically in executor `_approve_lesson`, CLI docs, and MCP context.
- `SessionSummary` uses `mtime_ns` (and `session_id` as a sort tie-breaker) so `list_sessions` matches “newest first” under coarse OS timestamps.

---

## Execution Handoff

**Status: execution complete** for the productionization scope above, including Task 13 Step 15. See **Implementation status (finalized)** for verification counts and plan-vs-code deltas.

For net-new work, write a dated follow-up plan under `docs/superpowers/plans/` rather than extending this checklist.
