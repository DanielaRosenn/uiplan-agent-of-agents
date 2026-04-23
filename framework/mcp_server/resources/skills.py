"""Expose loaded skills as MCP resources."""
from __future__ import annotations

import os
from pathlib import Path

from mcp.types import Resource

from mcp.server.lowlevel.helper_types import ReadResourceContents

from uipath_claude.skills.loader import load_skill_content
from uipath_claude.skills.registry import SkillRegistry


def _project_root() -> Path:
    return Path(os.environ.get("UIPATH_MCP_PROJECT_ROOT", os.getcwd())).resolve()


_registry: SkillRegistry | None = None


def _get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry(project_root=_project_root())
        _registry.load_skills()
    return _registry


async def get_skill_resources() -> list[Resource]:
    registry = _get_registry()
    resources: list[Resource] = []
    for skill in registry.skills:
        name = str(skill.get("name", ""))
        if not name:
            continue
        desc = (skill.get("description") or "")[:200]
        resources.append(
            Resource(
                uri=f"uipath://skill/{name}",
                name=name,
                description=desc,
                mimeType="text/markdown",
            )
        )
    return resources


async def fetch_skill_resource(uri: str) -> list[ReadResourceContents]:
    if not str(uri).startswith("uipath://skill/"):
        return [
            ReadResourceContents(
                content=f"Unsupported skill URI: {uri}",
                mime_type="text/plain",
            )
        ]
    skill_name = str(uri).replace("uipath://skill/", "", 1)
    registry = _get_registry()
    skill = registry.get_skill(skill_name)
    if not skill:
        return [
            ReadResourceContents(
                content=f"Skill not found: {skill_name}",
                mime_type="text/plain",
            )
        ]
    body = load_skill_content(skill)
    return [ReadResourceContents(content=body, mime_type="text/markdown")]
