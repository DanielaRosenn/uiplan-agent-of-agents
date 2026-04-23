"""Invoke Bedrock for a single agent turn."""
from uipath_claude.query.conversation import ConversationEngine


async def invoke_agent_llm(
    engine: ConversationEngine,
    system_prompt: str,
    user_message: str,
) -> str:
    """Run one model turn with role system prompt."""
    messages = [{"role": "user", "content": user_message}]
    return await engine.run(messages=messages, tools=[], system_prompt=system_prompt)
