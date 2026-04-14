"""Tests for SkillTool and model-backed create_skill_tool."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from uipath_claude.tools.skill_tool import SkillTool, create_skill_tool


@pytest.mark.asyncio
async def test_skill_tool_invoke_success(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        "---\nname: test-skill\ndescription: t\n---\n\n# Body\n", encoding="utf-8"
    )
    meta = {"name": "test-skill", "description": "t", "path": str(skill_file)}
    engine = AsyncMock()
    engine.run = AsyncMock(return_value="Generated workflow content")
    tool = SkillTool([meta], engine)
    result = await tool.invoke("test-skill", "create workflow", {})
    assert result.success
    assert "Generated workflow" in result.output


@pytest.mark.asyncio
async def test_skill_tool_detect_question(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("---\nname: uipath-rpa\ndescription: r\n---\n\n# RPA\n", encoding="utf-8")
    meta = {"name": "uipath-rpa", "description": "r", "path": str(skill_file)}
    engine = AsyncMock()
    engine.run = AsyncMock(
        return_value="Which email provider would you like to use, Outlook or Gmail?"
    )
    tool = SkillTool([meta], engine)
    result = await tool.invoke("uipath-rpa", "automate email", {})
    assert result.follow_up_required
    assert result.follow_up_question
    assert "email provider" in result.follow_up_question.lower()


@pytest.mark.asyncio
async def test_skill_tool_unknown_skill() -> None:
    engine = AsyncMock()
    tool = SkillTool([], engine)
    result = await tool.invoke("nonexistent-skill", "query", {})
    assert not result.success
    assert "not found" in result.errors[0].lower()


def test_create_skill_tool_with_engine_uses_invoke(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("---\nname: z\ndescription: d\n---\n\n# Z\n", encoding="utf-8")
    meta = {"name": "z", "description": "d", "path": str(skill_file)}
    engine = AsyncMock()
    engine.run = AsyncMock(return_value="ok")
    tool = create_skill_tool(meta, engine=engine)
    out = tool.invoke({"query": "q"})
    assert "ok" in out
