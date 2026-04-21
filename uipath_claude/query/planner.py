"""Planning agent module for UiPath Claude Code."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from uipath_claude.query.agentic_executor import AgenticExecutor, AgenticResult
from uipath_claude.tools.skill_execution_tools import get_planning_tools


DISCOVERY_AGENT_RELATIVE = Path("skills") / "agents" / "uipath-project-discovery-agent.md"
PROJECT_CONTEXT_RELATIVE = Path(".claude") / "rules" / "project-context.md"
DISCOVERY_MAX_AGE_SECONDS = 24 * 3600


async def run_planner_agent(
    user_request: str,
    project_context: dict[str, Any] | None = None,
    *,
    model_name: str | None = None,
    region: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> AgenticResult:
    """Run the read-only planning agent.

    ``model_name`` is accepted for backward compatibility but ignored — the
    executor's routing helper resolves the model from the ``agentic_executor``
    task tier.

    Args:
        user_request: The user's request
        project_context: Optional context
        model_name: Optional Bedrock model ID override (legacy).
        region: AWS region (defaults to ``AWS_REGION`` env var).

    Returns:
        AgenticResult containing the plan
    """
    system_prompt = """You are a software architect and planning specialist for UiPath Claude Code. Your role is to explore the codebase and design implementation plans.
You have access to read-only tools to explore the codebase. NEVER say you don't have access to tools or the local environment.

=== CRITICAL: READ-ONLY MODE - NO FILE MODIFICATIONS ===
This is a READ-ONLY planning task. You are STRICTLY PROHIBITED from:
- Creating new files
- Modifying existing files
- Deleting files
- Running ANY commands that change system state

Your role is EXCLUSIVELY to explore the codebase and design implementation plans. You do NOT have access to file editing tools.

## Your Process

1. **Understand Requirements**: Focus on the requirements provided.
2. **Explore Thoroughly**:
   - Read any relevant files
   - Find existing patterns and conventions
   - Understand the current architecture
3. **Design Solution**:
   - Create implementation approach
   - Consider trade-offs and architectural decisions
4. **Detail the Plan WITH TOOL-ACTIONABLE STEPS**:
   - Provide step-by-step implementation strategy
   - Name concrete tools the execution agent can call (not only human UI or generic CLI steps)
   - Identify dependencies and sequencing

## CRITICAL: Plans Must Be Executable by the Next Agent

A **separate execution agent** (not you) has write tools: `ensure_project_structure`, `write_file`,
`validate_and_fix_loop`, `deploy_to_orchestrator`, and the same read tools you have.

**You only have READ-ONLY tools:** `read_file`, `list_directory`, `read_project_json`, `find_activity_info`,
`query_uipath_docs` (and library readers). **Never invoke** `ensure_project_structure`, `write_file`, or any
write/scaffold tool — they are **not bound** to this planner; calling them will fail.

In your **written plan text**, tell the executor which tools to use and in what order (by name), e.g.
"The executor should call `read_project_json`, then `ensure_project_structure`, then add Main.xaml via
`write_file` or UIPATH_FILE blocks."

Avoid human-only primary steps (e.g. "open UiPath Studio and click…"). Prefer executor tool names over
generic "run uip new" unless you also map that to the equivalent executor tools above.

## Required Output

End your response with:

### Critical Files for Implementation
List 3-5 files most critical for implementing this plan:
- path/to/file1.xaml
- path/to/file2.py

REMEMBER: You can ONLY explore and plan. You CANNOT and MUST NOT write, edit, or modify any files. You do NOT have access to file editing tools."""

    tools = get_planning_tools()
    executor = AgenticExecutor(model_name=model_name, region=region)

    ctx = dict(project_context) if project_context else {}
    if "selected_skill_names" not in ctx:
        ctx = {**ctx, "selected_skill_names": ["uipath-planner"]}

    raw_cap = os.environ.get("UIPATH_PLANNER_MAX_ITERATIONS", "").strip()
    planner_max: int | None = None
    if raw_cap:
        try:
            planner_max = int(raw_cap)
        except ValueError:
            planner_max = None

    # We pass the system prompt as skill_content
    return await executor.execute(
        skill_content=system_prompt,
        user_request=user_request,
        tools=tools,
        project_context=ctx,
        skill_name="uipath-planner",
        max_iterations=planner_max,
        prior_messages=history,
    )


def _find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "CLAUDE.md").exists():
            return candidate
    return current


def _existing_context_is_fresh(path: Path, max_age_seconds: int) -> bool:
    if not path.exists():
        return False
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return False
    return (time.time() - mtime) <= max_age_seconds


async def _run_discovery_agent(
    user_request: str,
    repo_root: Path,
    *,
    executor: AgenticExecutor | None = None,
) -> str:
    """Invoke the uipath-project-discovery-agent and return its output.

    Tests monkeypatch this helper directly; the default implementation reads
    the agent's SKILL markdown from the pinned submodule and runs it via
    ``AgenticExecutor`` with the same read-only tool surface as the planner.
    """
    agent_path = repo_root / DISCOVERY_AGENT_RELATIVE
    if not agent_path.exists():
        raise FileNotFoundError(
            f"Discovery agent missing: {agent_path}. "
            "Ensure the UiPath/skills submodule is initialized."
        )
    agent_body = agent_path.read_text(encoding="utf-8")

    exe = executor or AgenticExecutor()
    result = await exe.execute(
        skill_content=agent_body,
        user_request=user_request,
        tools=get_planning_tools(),
        project_context={
            "selected_skill_names": ["uipath-project-discovery-agent"],
            "repo_root": str(repo_root),
        },
        skill_name="uipath-project-discovery-agent",
    )
    # AgenticResult exposes the final assistant text as .response_text.
    return getattr(result, "final_response", None) or str(result)


async def run_planner_agent_with_discovery(
    user_request: str,
    *,
    repo_root: str | Path | None = None,
    force_rediscover: bool = False,
    max_age_seconds: int = DISCOVERY_MAX_AGE_SECONDS,
    model_name: str | None = None,
    region: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> AgenticResult:
    """Run discovery first (if needed), then invoke the planner.

    1. If ``.claude/rules/project-context.md`` is younger than
       ``max_age_seconds`` and the caller did not pass ``force_rediscover``,
       skip discovery and use the cached file as context.
    2. Otherwise, invoke the ``uipath-project-discovery-agent`` from the
       pinned ``skills/`` submodule via ``AgenticExecutor`` and persist the
       returned document to ``.claude/rules/project-context.md``.
    3. Hand the context document to ``run_planner_agent`` as the
       ``project_context['discovery_document']`` entry.
    """
    root = Path(repo_root).resolve() if repo_root else _find_repo_root()
    context_path = root / PROJECT_CONTEXT_RELATIVE

    should_discover = (
        force_rediscover
        or not _existing_context_is_fresh(context_path, max_age_seconds)
    )

    discovery_doc: str
    if should_discover:
        discovery_doc = await _run_discovery_agent(user_request, root)
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.write_text(discovery_doc, encoding="utf-8")
    else:
        discovery_doc = context_path.read_text(encoding="utf-8")

    planner_context: dict[str, Any] = {
        "selected_skill_names": ["uipath-planner"],
        "discovery_document": discovery_doc,
        "discovery_source": str(context_path),
        "repo_root": str(root),
    }

    return await run_planner_agent(
        user_request,
        project_context=planner_context,
        model_name=model_name,
        region=region,
        history=history,
    )
