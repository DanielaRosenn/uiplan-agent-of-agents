"""Simple LLM answer for informational questions (no tools)."""

from __future__ import annotations

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


_SIMPLE_ANSWER_SYSTEM_PROMPT = """You are UiPath Claude Code, an AI assistant that helps users understand UiPath automation concepts.

You are answering an INFORMATIONAL QUESTION. Your job is to explain, describe, or clarify - NOT to build anything.

Rules:
- Provide clear, helpful explanations
- Use bullet points or numbered lists when appropriate
- Do NOT generate files, code blocks, XAML, or implementation plans
- Do NOT use file markers like <<<UIPATH_FILE>>> or ```path:
- Do NOT say "I'll create" or "Let me build" - just answer the question
- If the user wants you to build something, they will ask in a follow-up message

Answer the user's question directly and informatively."""


async def simple_llm_answer(
    user_input: str,
    history: list[dict[str, str]],
    *,
    model_name: str,
    region: str,
) -> str:
    """Answer an informational question without tools or file generation.

    Args:
        user_input: The user's question
        history: Conversation history as list of {"role": ..., "content": ...}
        model_name: Bedrock model ID
        region: AWS region

    Returns:
        String containing the answer
    """
    chat = ChatBedrockConverse(
        model=model_name,
        region_name=region,
    )

    messages: list[SystemMessage | HumanMessage | AIMessage] = [
        SystemMessage(content=_SIMPLE_ANSWER_SYSTEM_PROMPT)
    ]

    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_input))

    response = await chat.ainvoke(messages)
    return str(response.content)
