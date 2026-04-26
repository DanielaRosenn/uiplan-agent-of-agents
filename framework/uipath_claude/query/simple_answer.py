"""Simple LLM answer for informational questions (no tools)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from langchain_aws import ChatBedrockConverse  # noqa: F401  (re-exported so tests can patch)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from uipath_claude.llm.invoke import build_chat_model
from uipath_claude.llm.routing.complexity import ComplexitySignals


_SIMPLE_ANSWER_SYSTEM_PROMPT = """You are UiPath Claude Code, an AI assistant that helps users understand UiPath automation concepts and this local UiPath Builder Agent project.

You are answering an INFORMATIONAL QUESTION. Your job is to explain, describe, or clarify - NOT to build anything.

Rules:
- Provide clear, helpful explanations
- Use bullet points or numbered lists when appropriate
- Do NOT generate files, code blocks, XAML, or implementation plans
- Do NOT use file markers like <<<UIPATH_FILE>>> or ```path:
- Do NOT say "I'll create" or "Let me build" - just answer the question
- You are running inside the local UiPath Builder Agent CLI. If project capabilities are listed below, treat them as available through the host runtime.
- When a follow-up build or plan is implied, you may name the right slash command or next step, but this turn stays informational unless the host explicitly sent you here after a separate orchestration decision.
- If the system annotates that the orchestration router already selected the answer path for this turn, give a direct, complete answer; do not defer with "ask me to build" unless the user message is purely a meta-question.
- For questions like "can we use X?", answer from the listed skills and slash commands. Do NOT claim you have no access to skills, tools, or extensions just because this answer path is informational.
- When a slash command is the right entry point, name the command explicitly.

Answer the user's question directly and informatively."""


async def simple_llm_answer(
    user_input: str,
    history: list[dict[str, str]],
    *,
    model_name: str | None = None,
    region: str | None = None,
    stream: bool = False,
    on_delta: Callable[[str], None] | None = None,
    capabilities_context: str | None = None,
    after_orchestrator: bool = False,
) -> str:
    """Answer an informational question without tools or file generation.

    Args:
        user_input: The user's question
        history: Conversation history as list of {"role": ..., "content": ...}
        model_name: Optional Bedrock model ID override (legacy; routing helper
            normally resolves the model from the ``planner`` task tier).
        region: AWS region (defaults to ``AWS_REGION`` env var).
        stream: Whether to stream the response
        on_delta: Callback for streaming deltas
        capabilities_context: Optional local skill/command context for project-aware answers.

    Returns:
        String containing the answer
    """
    # #region agent log
    try:
        _dbg = {
            "sessionId": "7bfa30",
            "runId": "run1",
            "hypothesisId": "H2_H3",
            "location": "uipath_claude/query/simple_answer.py:simple_llm_answer:before_chat_init",
            "message": "Simple answer model selection",
            "data": {
                "model_name": model_name,
                "region": region,
                "cwd": str(Path.cwd()),
            },
            "timestamp": __import__("time").time_ns() // 1_000_000,
        }
        with open("debug-7bfa30.log", "a", encoding="utf-8") as _f:
            _f.write(json.dumps(_dbg, ensure_ascii=True) + "\n")
    except Exception:
        pass
    # #endregion

    chat = build_chat_model(
        task_id="planner",
        region=region,
        signals=ComplexitySignals(intent="question"),
        chat_cls=ChatBedrockConverse,
    )

    system_prompt = _SIMPLE_ANSWER_SYSTEM_PROMPT
    if capabilities_context and capabilities_context.strip():
        system_prompt = (
            f"{system_prompt}\n\n"
            "Local project capabilities available in this session:\n"
            f"{capabilities_context.strip()}"
        )
    if after_orchestrator:
        system_prompt = (
            f"{system_prompt}\n\n"
            "The orchestration router selected the informational/answer path for this "
            "turn. Answer the user's request directly using the context above; do not "
            "suggest a separate 'first ask' step unless a critical detail is missing."
        )

    messages: list[SystemMessage | HumanMessage | AIMessage] = [
        SystemMessage(content=system_prompt)
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
        full_response = ""
        async for chunk in chat.astream(messages):
            if hasattr(chunk, "content"):
                content = chunk.content
                if isinstance(content, str):
                    delta = content
                elif isinstance(content, list):
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
    suggestions = []

    answer_lower = answer.lower()
    question_lower = original_question.lower()

    if "project.json" in answer_lower or "project.json" in question_lower:
        suggestions.append("How do I add dependencies to project.json?")
        suggestions.append("What are the required fields in project.json?")

    if "main.xaml" in answer_lower or "workflow" in answer_lower or "main.xaml" in question_lower:
        suggestions.append("How do I create a new workflow file?")
        suggestions.append("What activities can I use in a workflow?")

    if "excel" in answer_lower or "office" in answer_lower:
        suggestions.append("How do I read data from an Excel file?")
        suggestions.append("What packages do I need for Excel automation?")

    if "orchestrator" in answer_lower:
        suggestions.append("How do I connect to Orchestrator?")
        suggestions.append("How do I publish to Orchestrator?")

    if not suggestions:
        suggestions.append("Can you show me an example?")
        suggestions.append("What are the best practices?")

    return suggestions[:4]
