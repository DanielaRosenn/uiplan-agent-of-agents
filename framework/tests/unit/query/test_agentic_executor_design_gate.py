"""Design-gate preflight + write-intent redirect in AgenticExecutor.

Covers the hardening added in docs/.../harden-builder-foundations plan:

- Pre-flight banner is printed (via progress.design_gate_banner) whenever the
  caller supplies a ``project_path`` that resolves on disk.
- A closed design gate makes write-intent tools short-circuit into a
  ``[REDIRECT]`` synthetic tool result (no real tool invocation).
- An open gate lets the write-intent tool run normally.
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from uipath_claude.query.agentic_executor import AgenticExecutor


@pytest.fixture()
def tmp_project(monkeypatch):
    """Isolated project dir + fresh design-store file."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "proj"
        proj.mkdir()
        store_path = Path(tmp) / "design_proposals.json"
        monkeypatch.setenv("UIPATH_DESIGN_STORE_PATH", str(store_path))
        monkeypatch.setenv("UIPATH_DESIGN_APPROVAL_ENABLED", "1")
        from uipath_claude.tools import design_store

        design_store.reset(in_memory_only=True)
        yield str(proj.resolve())
        design_store.reset(in_memory_only=True)


def _ai_with_write_file(project_dir: str, content: str = "hello") -> AIMessage:
    """AIMessage that calls write_file on a path inside the given project."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "write_file",
                "args": {
                    "file_path": str(Path(project_dir) / "Main.xaml"),
                    "content": content,
                    "project_dir": project_dir,
                },
                "id": "call_write_1",
                "type": "tool_call",
            }
        ],
    )


def _ai_finish(text: str = "done") -> AIMessage:
    return AIMessage(content=text)


_WRITE_CALLS: list[dict] = []


@tool
def write_file(file_path: str, content: str, project_dir: str = "") -> str:
    """Test double: records invocation via the module-level list."""
    _WRITE_CALLS.append(
        {"file_path": file_path, "content": content, "project_dir": project_dir}
    )
    return f"[OK] wrote {file_path}"


def test_preflight_banner_emitted_when_project_path_resolves(tmp_project):
    """progress.design_gate_banner fires once with approved=false / pending=none."""
    executor = AgenticExecutor(model_name="m", region="us-east-1")
    banner_calls: list[tuple] = []

    mock_progress = MagicMock()
    mock_progress.should_show_full_tool_body.return_value = False
    mock_progress.design_gate_banner.side_effect = (
        lambda *a, **kw: banner_calls.append((a, kw))
    )

    with patch(
        "uipath_claude.query.agentic_executor.AgenticProgressReporter",
        return_value=mock_progress,
    ), patch(
        "uipath_claude.query.agentic_executor.ChatBedrockConverse"
    ) as m_llm:
        llm_instance = m_llm.return_value
        llm_instance.bind_tools.return_value.ainvoke = AsyncMock(
            return_value=_ai_finish("ok")
        )
        asyncio.run(
            executor.execute(
                user_request="anything",
                skill_content="skill",
                skill_name="test",
                tools=[],
                project_context={"project_path": tmp_project},
                max_iterations=2,
            )
        )

    assert mock_progress.design_gate_banner.call_count == 1
    args, _ = banner_calls[0]
    banner_project, approved, pending = args
    assert Path(banner_project) == Path(tmp_project)
    assert approved is False
    assert pending is None


def test_write_intent_redirected_when_gate_closed(tmp_project):
    """write_file on an un-approved project returns [REDIRECT], tool not invoked."""
    _WRITE_CALLS.clear()
    executor = AgenticExecutor(model_name="m", region="us-east-1")

    with patch(
        "uipath_claude.query.agentic_executor.ChatBedrockConverse"
    ) as m_llm:
        llm_instance = m_llm.return_value
        llm_instance.bind_tools.return_value.ainvoke = AsyncMock(
            side_effect=[
                _ai_with_write_file(tmp_project),
                _ai_finish("stopping"),
            ]
        )
        result = asyncio.run(
            executor.execute(
                user_request="build it",
                skill_content="skill",
                skill_name="test",
                tools=[write_file],
                project_context={"project_path": tmp_project},
                max_iterations=3,
            )
        )

    assert _WRITE_CALLS == []
    redirected = [
        tc
        for tc in result.tool_calls_made
        if tc.get("name") == "write_file" and tc.get("ok") is False
    ]
    assert len(redirected) == 1
    assert result.tool_failure_count >= 1


def test_write_passes_through_when_gate_open(tmp_project):
    """Once the design is approved, write_file runs normally."""
    _WRITE_CALLS.clear()
    from uipath_claude.tools import design_store

    proposal, _warnings = design_store.propose(
        project_dir=tmp_project,
        title="t",
        summary="s",
        body="b",
    )
    design_store.approve(proposal.design_id)
    assert design_store.has_approved(tmp_project) is True

    executor = AgenticExecutor(model_name="m", region="us-east-1")
    with patch(
        "uipath_claude.query.agentic_executor.ChatBedrockConverse"
    ) as m_llm:
        llm_instance = m_llm.return_value
        llm_instance.bind_tools.return_value.ainvoke = AsyncMock(
            side_effect=[
                _ai_with_write_file(tmp_project),
                _ai_finish("done"),
            ]
        )
        result = asyncio.run(
            executor.execute(
                user_request="build it",
                skill_content="skill",
                skill_name="test",
                tools=[write_file],
                project_context={"project_path": tmp_project},
                max_iterations=3,
            )
        )

    assert len(_WRITE_CALLS) == 1
    assert result.tool_success_count >= 1


def test_preflight_skipped_without_project_path(monkeypatch):
    """No project_path and no UIPATH_PROJECT_DIR -> banner not emitted."""
    monkeypatch.delenv("UIPATH_PROJECT_DIR", raising=False)
    executor = AgenticExecutor(model_name="m", region="us-east-1")
    mock_progress = MagicMock()
    mock_progress.should_show_full_tool_body.return_value = False

    with patch(
        "uipath_claude.query.agentic_executor.AgenticProgressReporter",
        return_value=mock_progress,
    ), patch(
        "uipath_claude.query.agentic_executor.ChatBedrockConverse"
    ) as m_llm:
        llm_instance = m_llm.return_value
        llm_instance.bind_tools.return_value.ainvoke = AsyncMock(
            return_value=_ai_finish("ok")
        )
        asyncio.run(
            executor.execute(
                user_request="anything",
                skill_content="skill",
                skill_name="test",
                tools=[],
                max_iterations=2,
            )
        )

    assert mock_progress.design_gate_banner.call_count == 0
