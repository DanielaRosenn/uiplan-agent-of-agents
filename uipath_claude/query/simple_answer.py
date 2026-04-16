"""Simple LLM answer for informational questions (no tools)."""

from __future__ import annotations

from typing import Callable

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
    stream: bool = False,
    on_delta: Callable[[str], None] | None = None,
) -> str:
    """Answer an informational question without tools or file generation.

    Args:
        user_input: The user's question
        history: Conversation history as list of {"role": ..., "content": ...}
        model_name: Bedrock model ID
        region: AWS region
        stream: Whether to stream the response
        on_delta: Callback for streaming deltas

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

    if stream and on_delta:
        # Stream response
        full_response = ""
        async for chunk in chat.astream(messages):
            if hasattr(chunk, "content"):
                # Extract text from content
                content = chunk.content
                if isinstance(content, str):
                    delta = content
                elif isinstance(content, list):
                    # Handle list of content blocks
                    delta = ""
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            delta += block.get("text", "")
                        elif isinstance(block, str):
                            delta += block
                else:
                    delta = str(content)
                
                if delta:
                    full_response += delta
                    on_delta(delta)
        return full_response
    else:
        # Non-streaming response
        response = await chat.ainvoke(messages)
        return str(response.content)


def generate_followup_suggestions(answer: str, original_question: str) -> list[str]:
    """Generate follow-up question suggestions based on the answer.

    Args:
        answer: The answer that was provided
        original_question: The original question asked

    Returns:
        List of 2-4 follow-up question suggestions
    """
    # Simple heuristic-based suggestions
    suggestions = []
    
    answer_lower = answer.lower()
    question_lower = original_question.lower()
    
    # If answer mentions project.json, suggest related questions
    if "project.json" in answer_lower or "project.json" in question_lower:
        suggestions.append("How do I add dependencies to project.json?")
        suggestions.append("What are the required fields in project.json?")
    
    # If answer mentions Main.xaml or workflow
    if "main.xaml" in answer_lower or "workflow" in answer_lower or "main.xaml" in question_lower:
        suggestions.append("How do I create a new workflow file?")
        suggestions.append("What activities can I use in a workflow?")
    
    # If answer mentions Excel or Office
    if "excel" in answer_lower or "office" in answer_lower:
        suggestions.append("How do I read data from an Excel file?")
        suggestions.append("What packages do I need for Excel automation?")
    
    # If answer mentions Orchestrator
    if "orchestrator" in answer_lower:
        suggestions.append("How do I connect to Orchestrator?")
        suggestions.append("How do I publish to Orchestrator?")
    
    # Generic fallbacks
    if not suggestions:
        suggestions.append("Can you show me an example?")
        suggestions.append("What are the best practices?")
    
    return suggestions[:4]  # Return max 4 suggestions
