"""Lessons from the insights store are injected into the executor system prompt."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage

from uipath_claude.query.agentic_executor import AgenticExecutor
from uipath_claude.skills.insights import InsightLayer, InsightType, SkillInsight, SkillInsightsStore


def _ai(text: str) -> AIMessage:
    msg = AIMessage(content=text)
    msg.tool_calls = []
    return msg


def test_past_lessons_in_system_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("UIPATH_PROJECT_ROOT", str(tmp_path))
    store = SkillInsightsStore(project_root=tmp_path)
    store.append(
        SkillInsight(
            skill_name="uipath-automation",
            insight_type=InsightType.GOTCHA,
            content="Prefer validate_file after writes",
            success_count=4,
            failure_count=0,
        ),
        layer=InsightLayer.PROJECT,
    )

    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    captured: list[str] = []

    async def _fake_ainvoke(messages, *args, **kwargs):
        captured.append(str(messages[0].content))
        return _ai("done")

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        m_llm.return_value.bind_tools.return_value.ainvoke = AsyncMock(side_effect=_fake_ainvoke)
        asyncio.run(
            ex.execute(
                user_request="x",
                skill_content="body",
                skill_name="uipath-automation",
                tools=[],
                max_iterations=2,
            )
        )

    assert captured
    assert "## Past Lessons" in captured[0]
    assert "validate_file" in captured[0]
