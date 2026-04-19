"""Skill registry, matching, and insights MCP tools."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.types import Tool, ToolAnnotations

def _ro(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True)


def _staging(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    )

from uipath_claude.skills.insights import InsightLayer, InsightType, SkillInsight, SkillInsightsStore
from uipath_claude.skills.loader import load_skill_content
from uipath_claude.skills.lessons import load_for_skill
from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.skills.updater import check_for_updates, ensure_fresh, get_skills_info
from uipath_claude.tools.skill_insights_tool import SkillInsightsTool


_registry: SkillRegistry | None = None


def _project_root() -> Path:
    return Path(os.environ.get("UIPATH_MCP_PROJECT_ROOT", os.getcwd())).resolve()


def _get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry(project_root=_project_root())
        _registry.load_skills()
    return _registry


def get_skill_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_skill_list",
            description=(
                "Enumerate every loaded UiPath skill, optionally filtered by "
                "agent role (ba, sa, developer, qa, conversational). Read-only. "
                "Use for discovery; uipath_skill_match ranks by relevance to a "
                "user request, and uipath_skill_get loads the full markdown body."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_role": {
                        "type": "string",
                        "enum": ["ba", "sa", "developer", "qa", "conversational"],
                        "description": "Optional agent role filter.",
                    },
                },
            },
            annotations=_ro("List skills"),
        ),
        Tool(
            name="uipath_skill_get",
            description=(
                "Load the full markdown body of a single skill by name. "
                "Read-only. Use after uipath_skill_list or uipath_skill_match "
                "identifies the skill you want to apply."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Skill name as returned by uipath_skill_list.",
                    },
                },
                "required": ["skill_name"],
            },
            annotations=_ro("Read skill body"),
        ),
        Tool(
            name="uipath_skill_match",
            description=(
                "Rank skills by relevance to a free-form user input using the "
                "same heuristic as the CLI chat. Read-only. Use to pick which "
                "skill(s) to load with uipath_skill_get; for the full inventory "
                "use uipath_skill_list."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_input": {
                        "type": "string",
                        "description": "Free-text request to match skills against.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "How many ranked matches to return.",
                        "default": 3,
                    },
                },
                "required": ["user_input"],
            },
            annotations=_ro("Match skills to input"),
        ),
        Tool(
            name="uipath_skill_insights_query",
            description=(
                "Read operator-curated insights (gotchas, tips, decisions) for "
                "one skill, plus a short summary. Read-only. Insights are "
                "human-authored notes; for auto-promoted high-confidence "
                "failure patterns use uipath_skill_lessons_list."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Skill name to read insights for.",
                    },
                },
                "required": ["skill_name"],
            },
            annotations=_ro("Read skill insights"),
        ),
        Tool(
            name="uipath_skill_insights_add",
            description=(
                "Append a new insight (gotcha, failure_pattern, etc.) for a "
                "skill into the chosen layer (user, project, or shared). "
                "Stages locally; not committed to the shared submodule. Use for "
                "operator-curated notes; lessons promoted from observed failures "
                "go through uipath_skill_lessons_approve."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Skill the insight is about.",
                    },
                    "insight_type": {
                        "type": "string",
                        "description": "Kind of insight (e.g. gotcha, tip, failure_pattern).",
                    },
                    "content": {
                        "type": "string",
                        "description": "Insight body in markdown.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context (where you hit it).",
                    },
                    "layer": {
                        "type": "string",
                        "enum": ["user", "project", "shared"],
                        "description": "Storage layer; project is the default.",
                        "default": "project",
                    },
                },
                "required": ["skill_name", "insight_type", "content"],
            },
            annotations=_staging("Add skill insight"),
        ),
        Tool(
            name="uipath_skill_manifest",
            description=(
                "Return a JSON manifest of all loaded skills (names, origins, "
                "absolute paths). Read-only. Use to debug skill resolution and "
                "see which submodule version each skill came from."
            ),
            inputSchema={"type": "object", "properties": {}},
            annotations=_ro("Read skill manifest"),
        ),
        Tool(
            name="uipath_skill_check_updates",
            description=(
                "Report whether the skills git submodule (learning cache) has "
                "remote updates pending, with current and remote commit hashes. "
                "Read-only; does NOT mutate the cache. Run uipath_skill_update "
                "to actually pull."
            ),
            inputSchema={"type": "object", "properties": {}},
            annotations=_ro("Check skill updates"),
        ),
        Tool(
            name="uipath_skill_update",
            description=(
                "Refresh the skills submodule cache by fetching and resetting "
                "to the remote head, throttled to once every 6 hours unless "
                "force=true. Destructive: rewrites .git submodule state and "
                "the on-disk skills tree. Pair with uipath_skill_check_updates "
                "for a read-only preview."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "If true, bypass the 6h throttle.",
                        "default": False,
                    },
                },
            },
            annotations=ToolAnnotations(
                title="Refresh skills submodule cache",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
            ),
        ),
        Tool(
            name="uipath_skill_lessons_list",
            description=(
                "List high-confidence lessons (auto-promoted failure patterns) "
                "for a skill. Read-only. Lessons are derived from observed "
                "failures; for human-authored notes use uipath_skill_insights_query."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Skill to read lessons for.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max lessons to return, ranked by confidence.",
                        "default": 5,
                    },
                },
                "required": ["skill_name"],
            },
            annotations=_ro("List skill lessons"),
        ),
        Tool(
            name="uipath_skill_lessons_approve",
            description=(
                "Persist an approved lesson (failure pattern) for a skill into "
                "the project insights store. Destructive: appends to the "
                "skill insights database; use uipath_skill_lessons_list first "
                "to avoid duplicates."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Skill the lesson applies to.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Lesson body (failure pattern + remediation).",
                    },
                },
                "required": ["skill_name", "content"],
            },
            annotations=ToolAnnotations(
                title="Approve skill lesson (persists failure pattern)",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
            ),
        ),
    ]


async def call_skill_tool(name: str, arguments: dict[str, Any]) -> Any:
    registry = _get_registry()
    insights = SkillInsightsTool(project_root=_project_root())

    if name == "uipath_skill_list":
        role = arguments.get("agent_role")
        skills = registry.filter_by_agent(role) if role else registry.skills
        return [
            {
                "name": s.get("name"),
                "origin": s.get("origin"),
                "path": s.get("path", ""),
                "description": (s.get("description") or "")[:300],
            }
            for s in skills
        ]

    if name == "uipath_skill_get":
        skill = registry.get_skill(arguments["skill_name"])
        if not skill:
            return f"Skill not found: {arguments['skill_name']}"
        return load_skill_content(skill)

    if name == "uipath_skill_match":
        from uipath_claude.cli.app import _select_relevant_skills

        top_k = int(arguments.get("top_k", 3))
        selected = _select_relevant_skills(arguments["user_input"], registry.skills, max_items=top_k)
        return [
            {
                "name": s.get("name"),
                "origin": s.get("origin"),
                "description": (s.get("description") or "")[:400],
            }
            for s in selected
        ]

    if name == "uipath_skill_insights_query":
        return insights("query", arguments["skill_name"])

    if name == "uipath_skill_insights_add":
        return insights(
            "add",
            arguments["skill_name"],
            insight_type=arguments["insight_type"],
            content=arguments["content"],
            context=arguments.get("context"),
            layer=arguments.get("layer", "project"),
        )

    if name == "uipath_skill_manifest":
        return registry.generate_manifest()

    if name == "uipath_skill_check_updates":
        return uipath_skill_check_updates()

    if name == "uipath_skill_update":
        return uipath_skill_update(force=bool(arguments.get("force", False)))

    if name == "uipath_skill_lessons_list":
        return uipath_skill_lessons_list(
            arguments["skill_name"],
            limit=int(arguments.get("limit", 5)),
        )

    if name == "uipath_skill_lessons_approve":
        return uipath_skill_lessons_approve(arguments["skill_name"], arguments["content"])

    raise ValueError(f"Unknown skill tool: {name}")


def uipath_skill_check_updates() -> dict[str, Any]:
    has_updates, message, current, remote = check_for_updates()
    return {
        "has_updates": has_updates,
        "message": message,
        "current": current,
        "remote": remote,
    }


def uipath_skill_update(force: bool = False) -> dict[str, Any]:
    max_age = 0 if force else 6 * 3600
    status = ensure_fresh(max_age_seconds=max_age)
    info = get_skills_info()
    return {
        "status": status,
        "current_commit": info.get("current_commit"),
        "skills_count": info.get("skills_count"),
    }


def uipath_skill_lessons_list(skill_name: str, limit: int = 5) -> dict[str, Any]:
    project_root = Path(os.environ.get("UIPATH_MCP_PROJECT_ROOT", os.getcwd())).resolve()
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


def uipath_skill_lessons_approve(skill_name: str, content: str) -> dict[str, Any]:
    project_root = Path(os.environ.get("UIPATH_MCP_PROJECT_ROOT", os.getcwd())).resolve()
    insight = SkillInsight(
        skill_name=skill_name,
        insight_type=InsightType.FAILURE_PATTERN,
        content=content,
        source="cursor",
        failure_count=1,
    )
    SkillInsightsStore(project_root=project_root).append(insight, layer=InsightLayer.PROJECT)
    return {"ok": True, "skill": skill_name, "content_hash": insight.content_hash}
