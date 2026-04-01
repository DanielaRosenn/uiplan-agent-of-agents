"""Conversational agent node for free-form interaction."""

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import ProjectState
from agent.tools.skill_invoke import get_available_skills, invoke_skill


# Main conversational agent LLM
conversational_llm = ChatBedrockConverse(
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1",
    temperature=0.3,
).bind_tools([get_available_skills, invoke_skill])


CONVERSATIONAL_PROMPT = """
You are the UiPath Builder Agent - a conversational assistant for
building and managing UiPath RPA projects.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DYNAMIC SKILLS SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have access to a growing library of UiPath skills. Skills are
specialized agents that handle specific aspects of RPA development.

To discover available skills, call: get_available_skills()
To invoke a skill, call: invoke_skill(name, task, context)

When to invoke skills:
• User explicitly requests: "use the rpa-workflows skill to..."
• You determine a task needs specialized capability
• During project bootstrap (generation phase)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSATION MODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BOOTSTRAP MODE (/start-project):
  User provides process description → You guide through personas.

CONVERSATIONAL MODE (default):
  Free-form development conversation. Invoke skills as needed.

Current Mode: {mode}
Current Phase: {current_phase}
"""


async def conversational_agent(state: ProjectState) -> dict:
    """
    Main conversational agent node.

    Handles:
    - Free-form conversation
    - Skill invocation (auto or user-directed)
    - Mode transitions (bootstrap → conversational)

    Args:
        state: Current ProjectState

    Returns:
        Updated state with new messages
    """
    mode = state.get("mode", "conversational")
    current_phase = state.get("current_phase", "dev")

    system_prompt = CONVERSATIONAL_PROMPT.format(
        mode=mode,
        current_phase=current_phase,
    )

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state.get("messages", []))

    response = await conversational_llm.ainvoke(messages)

    # Update state with response
    return {
        "messages": state.get("messages", []) + [response],
    }
