"""Tests for Bedrock-safe tool name normalization in AgenticExecutor."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from uipath_claude.query.agentic_executor import (
    _normalize_tool_calls_on_ai_response,
    _normalize_tool_name_for_bedrock,
    _strip_last_ai_tool_calls,
)


def test_normalize_valid_name_unchanged() -> None:
    name, bad = _normalize_tool_name_for_bedrock("browse_book_toc")
    assert name == "browse_book_toc"
    assert bad is False


def test_normalize_strips_xml_runoff() -> None:
    raw = 'browse_book_toc" >\n<parameter name="book_id'
    name, bad = _normalize_tool_name_for_bedrock(raw)
    assert name == "browse_book_toc"
    assert bad is True


def test_normalize_truncates_to_64() -> None:
    long_name = "a" * 65
    name, bad = _normalize_tool_name_for_bedrock(long_name)
    assert name == "a" * 64
    assert bad is True


def test_normalize_empty_is_invalid_tool() -> None:
    name, bad = _normalize_tool_name_for_bedrock("")
    assert name == "invalid_tool"
    assert bad is True


def test_normalize_tool_calls_on_ai_response_mutates() -> None:
    raw = 'browse_book_toc" >'
    msg = AIMessage(
        content="",
        tool_calls=[{"id": "t1", "name": raw, "args": {"book_id": "x"}}],
    )
    _normalize_tool_calls_on_ai_response(msg)
    assert msg.tool_calls[0]["name"] == "browse_book_toc"


def test_strip_last_ai_tool_calls_removes_tool_calls() -> None:
    messages: list = [
        AIMessage(content="hi", tool_calls=[{"id": "1", "name": "x", "args": {}}]),
    ]
    _strip_last_ai_tool_calls(messages)
    assert messages[0].tool_calls == []
