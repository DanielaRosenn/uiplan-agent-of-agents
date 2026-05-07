# Learning Loop (Hermes-style)

This repository ships an end-to-end learning pipeline modeled after the Hermes
agents that mutates *how the agent answers next time* based on *what happened
last time*. The loop is fully in-tree - there is no hosted service.

This document describes the wiring as it exists today and points at the
integration test that pins the contract.

## Pipeline

```text
AgenticExecutor / MCP tool call
        |
        v
SkillExecutionContext          uipath_claude/skills/execution_hook.py
        |
        | SkillUsageEvent
        v
SkillUsageTracker              uipath_claude/skills/usage_tracker.py
        |                      (auto-capture rules on failure, complex
        |                      success, recovery)
        v
SkillInsightsStore             uipath_claude/skills/insights.py
        |                      (layered: user / project / shared)
        v
lessons.load_for_skill         uipath_claude/skills/lessons.py
        |                      (ranks + filters by confidence)
        v
System prompt injection        AgenticExecutor._prepend_lessons(...)
        |
        v
Next skill run uses the lessons as context
```

In parallel, the **upstream scanner** watches the pinned `UiPath/skills`
submodule for new skills/tools:

```text
scan_upstream()                uipath_claude/skills/upstream_scan.py
        -> take_snapshot()  (commit + skill ids + tool dirs)
        -> compute_diff(prev, current)
        -> save_snapshot()  (persists to .uipath-claude/skills.snapshot.json)
```

`FeedbackLoop` in `uipath_claude/query/feedback_loop.py` closes the short
loop with the user in the chat surface: when a response contains a
clarifying question, the loop re-arms the executor with the user reply
instead of returning control.

## Auto-capture rules

Implemented in `SkillUsageTracker._check_auto_capture`:

| Trigger                                   | Insight type       |
|-------------------------------------------|--------------------|
| Any failure (`success=False`)             | `failure_pattern`  |
| Success after a recent failure in session | `success_pattern`  |
| Success with `tool_calls >= 5`            | `edge_case`        |

Failures always auto-capture (`auto_capture_on_failure=True` by default).
Recovery and complexity are configurable via `UsageTrackerConfig`.

## Storage layers

`SkillInsightsStore` resolves insights first-wins across three layers, so a
user can override a project default and a project can override a shared
default:

1. User - `~/.cursor/skill-insights/<skill>.json`
2. Project - `.uipath-claude/skill-insights/<skill>.json`
3. Shared - `extensions/skill-insights/<skill>.json`

Insights are deduplicated by `content_hash` (MD5 of the normalized content).

## Consumption

- Planner (`run_planner_agent_with_discovery`) and persona Q&A
  (`persona_router.answer_question`) both pass skill names into the
  `AgenticExecutor`, which calls `lessons.load_for_skill` and prepends a
  compact "Past Lessons" block to the system prompt.
- The submodule guard (`uipath_claude/skills/submodule_guard.py`) runs on
  session start and in git hooks so the loop can trust the upstream snapshot.
- `scan_upstream` runs opportunistically (e.g. after the guard passes) and
  surfaces diffs via `UpstreamDiff.has_changes()` so operators know when a
  new official UiPath skill landed upstream.

## Contract test

The contract is pinned by
`tests/integration/test_learning_loop_integration.py`. It exercises the
real modules (no mocks except `HOME` redirection) and covers:

1. Failure capture -> `failure_pattern` insight in the store.
2. Complex-success capture -> `edge_case` insight.
3. Recovery capture -> `success_pattern` insight.
4. `lessons.load_for_skill` + `render_lessons_block` surface a high-
   confidence insight from the store.
5. `upstream_scan.take_snapshot` + `compute_diff` detect a newly added
   skill in the pinned submodule.
6. End-to-end: a failure recorded via `SkillExecutionContext` is retrievable
   via `lessons.load_for_skill` once its confidence crosses the threshold.
7. `create_usage_tracker(project_root)` wires the store at the expected
   project path.

Run it with:

```bash
uv run --no-sync pytest tests/integration/test_learning_loop_integration.py
```

Any change to the learning loop modules must keep this test green.
