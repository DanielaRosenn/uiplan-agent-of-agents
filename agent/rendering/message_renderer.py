"""Render LLM messages to human-readable terminal output."""

from typing import Any, List
from langchain_core.messages import AIMessage


def render_message(message: AIMessage) -> str:
    """
    Render an AIMessage to human-readable text.

    Args:
        message: LangChain AIMessage

    Returns:
        Formatted string for terminal output
    """
    content = message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return render_content_blocks(content)

    return str(content)


def render_content_blocks(blocks: List[dict]) -> str:
    """
    Render a list of content blocks to text.

    Handles:
    - text blocks: merged into output
    - tool_use blocks: shown as progress indicators
    - tool_result blocks: summarized (not full content)

    Args:
        blocks: List of content block dicts

    Returns:
        Formatted string
    """
    parts = []

    for block in blocks:
        block_type = block.get("type", "unknown")

        if block_type == "text":
            text = block.get("text", "")
            parts.append(text)

        elif block_type == "tool_use":
            tool_name = block.get("name", "unknown")
            parts.append(f"\n[Using tool: {tool_name}]\n")

        elif block_type == "tool_result":
            tool_id = block.get("tool_use_id", "unknown")
            content = block.get("content", "")
            summary = _summarize_content(content, max_len=100)
            parts.append(f"[Tool result: {summary}]\n")

        else:
            parts.append(f"[{block_type}]")

    return "".join(parts)


def _summarize_content(content: Any, max_len: int = 100) -> str:
    """Summarize content to max length."""
    text = str(content)
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."
