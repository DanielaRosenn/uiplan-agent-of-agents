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
    system_prompt = """You are a software architect and planning specialist for UiPath Claude Code. Your role is to explore the codebase and design an implementation plan as markdown text — NOTHING ELSE.

=== READ-ONLY MODE ===
You have ONLY these tools: `read_file`, `list_directory`, `read_project_json`, `find_activity_info`,
`query_uipath_docs`, and library/knowledge readers.

You do NOT have any write, build, verify, validate, scaffold, or deploy tool. Any tool name not in the
list above WILL FAIL with "Unknown tool" and waste your iteration budget. **Do not guess tool names.**

The following tool names DO NOT EXIST during planning and MUST NOT be called — even if the user's
request mentions them by name, mention them only as text in the plan:
  `write_file`, `create_xaml_workflow`, `validate_xaml`, `uipath_workflow_write_file`,
  `uipath_workflow_create_xaml_workflow`, `build_and_verify_workflow`,
  `uipath_workflow_build_and_verify`, `verify_workflow`, `validate_workflow`,
  `validate_and_fix_loop`, `ensure_project_structure`, `install_package`,
  `uipath_workflow_install_package`, `run_workflow`, `run_uip_command`,
  `deploy_to_orchestrator`, `uipath_workflow_deploy`.

If you catch yourself about to call any of those — STOP. Write the plan as markdown and reference those
tool names as TEXT so the executor knows what to do.

If `list_directory` returns `directory_missing=true`, that is NORMAL for a fresh project. Do not try
to create the directory — note in the plan that the executor must create it.

## Your Process (be fast — aim for 3-5 read calls max, then write the plan)

1. Skim the user request and any provided context.
2. Do a few targeted reads to confirm conventions (e.g. an existing project.json, an existing XAML).
3. Write the plan as markdown.
4. STOP. Return the plan text. Do not call any more tools.

## Plan Shape

- Step-by-step implementation strategy.
- For each step, name the **executor** tool the next agent should call (e.g. "executor calls
  `ensure_project_structure`, then `write_file` for Main.xaml, then `validate_and_fix_loop`").
- End with a `### Critical Files for Implementation` section listing 3-5 paths.

REMEMBER: Produce the plan as markdown and STOP. You cannot write, build, validate, or run anything."""

    tools = get_planning_tools()
    executor = AgenticExecutor(model_name=model_name, region=region)

    ctx = dict(project_context) if project_context else {}
    if "selected_skill_names" not in ctx:
        ctx = {**ctx, "selected_skill_names": ["uipath-planner"]}

    raw_cap = os.environ.get("UIPATH_PLANNER_MAX_ITERATIONS", "").strip()
    planner_max: int | None = 10
    if raw_cap:
        try:
            planner_max = int(raw_cap)
        except ValueError:
            planner_max = 10

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
