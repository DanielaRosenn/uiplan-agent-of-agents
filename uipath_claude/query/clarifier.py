"""Clarification agent for ambiguous user requests."""

from __future__ import annotations

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage


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
