"""Business Analyst persona node for requirements gathering."""

import json
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from agent.state import ProjectState


ba_llm = ChatBedrockConverse(
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1",
    temperature=0.3,
)

BA_SYSTEM_PROMPT = """
You are a Business Analyst for UiPath RPA projects.

Your job is to gather requirements from the user and produce a Process Design Document (PDD).

WORKFLOW:
1. Read the user's process description
2. If the description is vague or missing key details, ask ONE clarifying question
3. If the description is sufficient, generate a PDD

When you have enough information, output a PDD as a JSON block wrapped in ```json ... ```:
{
  "process_name": "<name>",
  "process_description": "<detailed description>",
  "trigger": "<what starts the process>",
  "input_data": ["<list of inputs>"],
  "output_data": ["<list of outputs>"],
  "steps": [
    {"step": 1, "description": "<step description>", "application": "<app used>"}
  ],
  "business_rules": ["<rule 1>"],
  "exceptions": ["<exception scenario>"],
  "frequency": "<how often the process runs>",
  "volume": "<number of transactions per run>"
}

If you need clarification, do NOT output JSON. Instead ask a clear, specific question.

IMPORTANT: Only output the JSON PDD when you have sufficient information. One round of
clarification is acceptable.
"""


def _extract_json_from_response(content: str) -> dict | None:
    """Try to extract a JSON block from the LLM response."""
    # Look for ```json ... ``` blocks
    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        try:
            return json.loads(content[start:end].strip())
        except json.JSONDecodeError:
            pass
    # Try parsing the whole content as JSON
    try:
        return json.loads(content.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    return None


async def ba_persona(state: ProjectState) -> dict:
    """
    BA persona node: gathers requirements and generates PDD.

    If the user's description is sufficient, generates a PDD and sets
    needs_clarification=False. Otherwise asks a clarifying question.
    """
    messages = [SystemMessage(content=BA_SYSTEM_PROMPT)]
    messages.extend(state.get("messages", []))

    try:
        response = await ba_llm.ainvoke(messages)
    except Exception as e:
        error_msg = f"BA Error: {type(e).__name__}: {str(e)}"
        return {
            "messages": [AIMessage(content=error_msg)],
            "current_phase": "ba",
        }

    content = response.content if isinstance(response.content, str) else str(response.content)

    # Check if the response contains a PDD (JSON)
    pdd = _extract_json_from_response(content)

    if pdd:
        return {
            "messages": [AIMessage(content=content)],
            "pdd": pdd,
            "needs_clarification": False,
            "current_phase": "ba",
            "project_name": pdd.get("process_name", "UntitledProject"),
        }
    else:
        # BA is asking a clarifying question
        return {
            "messages": [AIMessage(content=content)],
            "needs_clarification": True,
            "clarify_question": content,
            "current_phase": "ba",
        }
