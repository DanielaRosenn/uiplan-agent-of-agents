"""Clarification agent for ambiguous user requests."""

from __future__ import annotations

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


_CLARIFIER_SYSTEM_PROMPT = """You are a helpful assistant for UiPath automation. The user's request is ambiguous or missing critical details.

Your ONLY job is to ask 2-3 specific clarifying questions to understand:
1. What system, application, or data source they want to automate
2. What specific actions they need (read, write, send, process, etc.)
3. What inputs/outputs are expected

Rules:
- Ask questions in a numbered list format
- Be concise - no more than 3 questions
- Do NOT generate any code, XAML, implementation plans, or file contents
- Do NOT make assumptions about what the user wants
- Do NOT say "I'll create" or "I'll build" - only ask questions

Example response format:
To help you build the right automation, I have a few questions:
1. Which email provider do you use (Outlook, Gmail, etc.)?
2. Do you need to read emails, send emails, or both?
3. What should happen with the emails after processing?"""


_INCREMENTAL_CLARIFIER_PROMPT = """You are a helpful assistant for UiPath automation. You are clarifying an ambiguous request one question at a time.

Context:
- Original request: {original_request}
- Questions asked so far: {questions_asked}
- Answers received: {answers_received}

Your job is to:
1. Analyze what information is still missing to build the automation
2. Ask ONE focused, specific question to gather the next most important piece of information
3. If you have enough information to proceed with building, respond with EXACTLY: "READY_TO_BUILD"

Rules:
- Ask only ONE question per turn
- Be specific and clear
- Do NOT generate code, XAML, or implementation plans
- Do NOT make assumptions
- When you have enough details (system/app, action, inputs/outputs), say "READY_TO_BUILD"

Your response (one question OR "READY_TO_BUILD"):"""


async def run_clarifier_agent(
    user_request: str,
    *,
    model_name: str,
    region: str,
) -> str:
    """Ask clarifying questions for an ambiguous request.

    Args:
        user_request: The ambiguous user request
        model_name: Bedrock model ID
        region: AWS region

    Returns:
        String containing clarifying questions
    """
    chat = ChatBedrockConverse(
        model=model_name,
        region_name=region,
    )

    messages = [
        SystemMessage(content=_CLARIFIER_SYSTEM_PROMPT),
        HumanMessage(content=f"User request: {user_request}"),
    ]

    response = await chat.ainvoke(messages)
    return str(response.content)


async def generate_next_clarifying_question(
    original_request: str,
    questions_asked: list[str],
    answers_received: list[str],
    *,
    model_name: str,
    region: str,
) -> str:
    """Generate the next clarifying question based on context.

    Args:
        original_request: The original ambiguous request
        questions_asked: List of questions already asked
        answers_received: List of answers received
        model_name: Bedrock model ID
        region: AWS region

    Returns:
        Next question to ask, or "READY_TO_BUILD" if enough info collected
    """
    chat = ChatBedrockConverse(
        model=model_name,
        region_name=region,
    )

    questions_str = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions_asked)) if questions_asked else "None"
    answers_str = "\n".join(f"{i+1}. {a}" for i, a in enumerate(answers_received)) if answers_received else "None"

    prompt = _INCREMENTAL_CLARIFIER_PROMPT.format(
        original_request=original_request,
        questions_asked=questions_str,
        answers_received=answers_str,
    )

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="What should I ask next?"),
    ]

    response = await chat.ainvoke(messages)
    return str(response.content).strip()


def should_transition_to_build(response: str) -> bool:
    """Check if clarification is complete and ready to build.

    Args:
        response: Response from generate_next_clarifying_question

    Returns:
        True if ready to build, False if more questions needed
    """
    return "READY_TO_BUILD" in response.upper()
