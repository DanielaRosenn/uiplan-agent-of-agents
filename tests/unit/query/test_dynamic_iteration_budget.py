"""Dynamic iteration budget in ``AgenticExecutor``.

When the executor reaches ``max_iter`` while the last 5 tool calls contain
at least 2 successes, it should extend the budget once by
``UIPATH_MAX_ITER_EXTEND`` (default 10). The extension:

- Fires exactly once per run (never twice).
- Is disabled by ``UIPATH_MAX_ITER_EXTEND=0``.
- Only happens when recent activity shows success signals.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from uipath_claude.query.agentic_executor import AgenticExecutor


@tool
def _noop_success(value: str = "") -> str:
    """Test double: always succeeds."""
    return f"[OK] noop {value}"


def _ai_call(call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "_noop_success",
                "args": {"value": call_id},
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def _run(executor: AgenticExecutor, *, max_iterations: int, llm_mock) -> object:
    return asyncio.run(
        executor.execute(
            user_request="loop",
            skill_content="skill",
            skill_name="test",
            tools=[_noop_success],
            max_iterations=max_iterations,
        )
    )


def test_budget_extends_once_when_progress_detected(monkeypatch) -> None:
    monkeypatch.setenv("UIPATH_MAX_ITER_EXTEND", "10")
    executor = AgenticExecutor(model_name="m", region="us-east-1")
    mock_progress = MagicMock()
    mock_progress.should_show_full_tool_body.return_value = False

    # Always emit a tool call so every iteration produces a successful call.
    side_effect = [_ai_call(f"c{i}") for i in range(30)]

    with patch(
        "uipath_claude.query.agentic_executor.AgenticProgressReporter",
        return_value=mock_progress,
    ), patch(
        "uipath_claude.query.agentic_executor.ChatBedrockConverse"
    ) as m_llm:
        bound = m_llm.return_value.bind_tools.return_value
        bound.ainvoke = AsyncMock(side_effect=side_effect)
        result = _run(executor, max_iterations=3, llm_mock=m_llm)

    # Initial cap 3, extended once by +10 = 14 iterations total.
    assert result.iterations >= 4
    assert result.iterations <= 13
    info_messages = [c.args[0] for c in mock_progress.info.call_args_list if c.args]
    assert any("BUDGET_EXTENDED" in m for m in info_messages), (
        f"Expected a BUDGET_EXTENDED info line, saw: {info_messages}"
    )
    # Only ever extends once.
    assert sum("BUDGET_EXTENDED" in m for m in info_messages) == 1


def test_budget_extension_respects_env_var_disabled(monkeypatch) -> None:
    monkeypatch.setenv("UIPATH_MAX_ITER_EXTEND", "0")
    executor = AgenticExecutor(model_name="m", region="us-east-1")
    mock_progress = MagicMock()
    mock_progress.should_show_full_tool_body.return_value = False

    side_effect = [_ai_call(f"c{i}") for i in range(30)]

    with patch(
        "uipath_claude.query.agentic_executor.AgenticProgressReporter",
        return_value=mock_progress,
    ), patch(
        "uipath_claude.query.agentic_executor.ChatBedrockConverse"
    ) as m_llm:
        bound = m_llm.return_value.bind_tools.return_value
        bound.ainvoke = AsyncMock(side_effect=side_effect)
        result = _run(executor, max_iterations=3, llm_mock=m_llm)

    # No extension: should terminate at max_iterations exactly.
    assert result.iterations == 3
    info_messages = [c.args[0] for c in mock_progress.info.call_args_list if c.args]
    assert not any("BUDGET_EXTENDED" in m for m in info_messages)


def test_budget_does_not_extend_without_progress(monkeypatch) -> None:
    """If the LLM stops calling tools, budget should not bump."""
    monkeypatch.setenv("UIPATH_MAX_ITER_EXTEND", "10")
    executor = AgenticExecutor(model_name="m", region="us-east-1")
    mock_progress = MagicMock()
    mock_progress.should_show_full_tool_body.return_value = False

    # Plain AIMessage with no tool_calls => loop completes at iteration 1.
    with patch(
        "uipath_claude.query.agentic_executor.AgenticProgressReporter",
        return_value=mock_progress,
    ), patch(
        "uipath_claude.query.agentic_executor.ChatBedrockConverse"
    ) as m_llm:
        bound = m_llm.return_value.bind_tools.return_value
        bound.ainvoke = AsyncMock(return_value=AIMessage(content="done"))
        result = _run(executor, max_iterations=3, llm_mock=m_llm)

    info_messages = [c.args[0] for c in mock_progress.info.call_args_list if c.args]
    assert not any("BUDGET_EXTENDED" in m for m in info_messages)
    assert result.iterations == 1
