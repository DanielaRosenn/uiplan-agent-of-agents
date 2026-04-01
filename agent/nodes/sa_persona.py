"""Solution Architect persona node for technical design."""

import json
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from agent.state import ProjectState
from agent.prompts.constraints import HARD_CONSTRAINTS


sa_llm = ChatBedrockConverse(
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1",
    temperature=0.2,
)

SA_SYSTEM_PROMPT = """
You are a Solution Architect for UiPath RPA projects.

{hard_constraints}

Given a Process Design Document (PDD), produce a Solution Design Document (SDD).

The SDD must be a JSON block wrapped in ```json ... ```:
{{
  "project_name": "<PascalCase project name>",
  "namespace": "<Company.Department.ProjectName>",
  "template_type": "coded-workflow",
  "target_framework": "Windows",
  "language": "C#",
  "coded_activities": [
    {{
      "class_name": "<ActivityName>",
      "purpose": "<what it does>",
      "inputs": ["<input args>"],
      "outputs": ["<output values>"],
      "dependencies": ["<NuGet packages>"]
    }}
  ],
  "config_keys": [
    {{
      "key": "<ConfigKeyName>",
      "description": "<what it configures>",
      "default_value": "<default>"
    }}
  ],
  "nuget_packages": [
    "UiPath.System.Activities",
    "UiPath.UIAutomation.Activities"
  ],
  "complexity": "simple|moderate|complex",
  "hitl_reason": "<why HITL review is needed, or null if not needed>"
}}

Rules:
- Always use C# and Modern activities
- Target framework is always Windows
- Set complexity to "complex" if: more than 3 coded activities, external integrations, or
  multiple exception paths
- If complexity is "complex", HITL review is needed (provide hitl_reason)
- If complexity is "simple" or "moderate", set hitl_reason to null
"""


def _extract_json_from_response(content: str) -> dict | None:
    """Try to extract a JSON block from the LLM response."""
    if "```json" in content:
        start = content.index("```json") + 7
        end = content.index("```", start)
        try:
            return json.loads(content[start:end].strip())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(content.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    return None


async def sa_persona(state: ProjectState) -> dict:
    """
    SA persona node: reads PDD and generates SDD.

    Determines whether HITL review is required based on project complexity.
    """
    pdd = state.get("pdd", {})

    system_prompt = SA_SYSTEM_PROMPT.format(hard_constraints=HARD_CONSTRAINTS)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Generate an SDD for this PDD:\n\n{json.dumps(pdd, indent=2)}"),
    ]

    try:
        response = await sa_llm.ainvoke(messages)
    except Exception as e:
        error_msg = f"SA Error: {type(e).__name__}: {str(e)}"
        return {
            "messages": [AIMessage(content=error_msg)],
            "current_phase": "sa",
        }

    content = response.content if isinstance(response.content, str) else str(response.content)
    sdd = _extract_json_from_response(content)

    if sdd:
        complexity = sdd.get("complexity", "simple")
        requires_hitl = complexity == "complex"

        return {
            "messages": [AIMessage(content=content)],
            "sdd": sdd,
            "requires_hitl": requires_hitl,
            "current_phase": "sa",
            "project_name": sdd.get("project_name", state.get("project_name", "UntitledProject")),
            "template_type": sdd.get("template_type", "coded-workflow"),
        }
    else:
        # Fallback: SA couldn't produce valid SDD
        return {
            "messages": [AIMessage(content=f"SA could not produce a valid SDD. Raw output:\n{content}")],
            "current_phase": "sa",
            "requires_hitl": False,
            "sdd": {},
        }
