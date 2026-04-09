# tests/unit/test_message_renderer.py
"""Unit tests for message renderer."""

import pytest
from langchain_core.messages import AIMessage

from agent.rendering.message_renderer import render_message, render_content_blocks


class TestMessageRenderer:
    """Tests for render_message function."""

    def test_renders_text_content(self):
        """Text content renders as plain text."""
        message = AIMessage(content="Hello, world!")
        result = render_message(message)
        assert result == "Hello, world!"

    def test_renders_text_blocks(self):
        """List of text blocks renders as merged text."""
        blocks = [
            {"type": "text", "text": "First part."},
            {"type": "text", "text": " Second part."},
        ]
        result = render_content_blocks(blocks)
        assert result == "First part. Second part."

    def test_renders_tool_use_as_progress(self):
        """tool_use blocks show tool name."""
        blocks = [
            {"type": "tool_use", "name": "get_available_skills", "id": "call_1"},
        ]
        result = render_content_blocks(blocks)
        assert "get_available_skills" in result
        assert "Using tool:" in result or "Tool:" in result

    def test_hides_tool_result_details(self):
        """tool_result blocks show summary, not full content."""
        blocks = [
            {"type": "tool_result", "tool_use_id": "call_1", "content": "x" * 1000},
        ]
        result = render_content_blocks(blocks)
        assert len(result) < 500


class TestRenderContentBlocks:
    """Additional tests for render_content_blocks."""

    def test_empty_blocks_returns_empty_string(self):
        """Empty block list returns empty string."""
        result = render_content_blocks([])
        assert result == ""

    def test_unknown_block_type_shows_type(self):
        """Unknown block types show their type in brackets."""
        blocks = [{"type": "custom_type"}]
        result = render_content_blocks(blocks)
        assert "custom_type" in result

    def test_mixed_content_blocks(self):
        """Mixed block types render in order."""
        blocks = [
            {"type": "text", "text": "Starting..."},
            {"type": "tool_use", "name": "search", "id": "call_1"},
            {"type": "text", "text": "Done."},
        ]
        result = render_content_blocks(blocks)
        assert "Starting..." in result
        assert "search" in result
        assert "Done." in result

    def test_message_with_list_content(self):
        """AIMessage with list content uses render_content_blocks."""
        blocks = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": " World"},
        ]
        message = AIMessage(content=blocks)
        result = render_message(message)
        assert "Hello" in result
        assert "World" in result
