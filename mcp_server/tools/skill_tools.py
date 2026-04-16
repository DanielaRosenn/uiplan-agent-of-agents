"""Skill registry, matching, and insights MCP tools."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.types import Tool

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
            description="List UiPath skills (optional filter by agent role: ba, sa, developer, qa, conversational)",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_role": {
                        "type": "string",
                        "enum": ["ba", "sa", "developer", "qa", "conversational"],
                    },
                },
            },
        ),
        Tool(
            name="uipath_skill_get",
            description="Load full markdown body for one skill by name",
            inputSchema={
                "type": "object",
                "properties": {"skill_name": {"type": "string"}},
                "required": ["skill_name"],
            },
        ),
        Tool(
            name="uipath_skill_match",
            description="Score and return best-matching skills for free-form user input (same heuristic as CLI chat)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_input": {"type": "string"},
                    "top_k": {"type": "integer", "default": 3},
                },
                "required": ["user_input"],
            },
        ),
        Tool(
            name="uipath_skill_insights_query",
            description="Query skill insights (summary + raw list) via SkillInsightsTool",
            inputSchema={
                "type": "object",
                "properties": {"skill_name": {"type": "string"}},
                "required": ["skill_name"],
            },
        ),
        Tool(
            name="uipath_skill_insights_add",
            description="Add a skill insight (gotcha, failure_pattern, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string"},
                    "insight_type": {"type": "string"},
                    "content": {"type": "string"},
                    "context": {"type": "string"},
                    "layer": {
                        "type": "string",
                        "enum": ["user", "project", "shared"],
                        "default": "project",
                    },
                },
                "required": ["skill_name", "insight_type", "content"],
            },
        ),
        Tool(
            name="uipath_skill_manifest",
            description="JSON manifest of all loaded skills (names, origins, paths)",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="uipath_skill_check_updates",
            description="Check whether the skills submodule (learning cache) has updates",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="uipath_skill_update",
            description="Refresh skills submodule cache (force=true bypasses 6h throttle)",
            inputSchema={
                "type": "object",
                "properties": {"force": {"type": "boolean", "default": False}},
            },
        ),
        Tool(
            name="uipath_skill_lessons_list",
            description="List high-confidence lessons for a skill",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["skill_name"],
            },
        ),
        Tool(
            name="uipath_skill_lessons_approve",
            description="Persist an approved lesson (failure pattern) for a skill",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["skill_name", "content"],
            },
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
