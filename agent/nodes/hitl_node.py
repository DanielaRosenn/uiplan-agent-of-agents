"""Human-in-the-Loop review node."""

import json
from langchain_core.messages import AIMessage, HumanMessage
from agent.state import ProjectState


HITL_DISPLAY_TEMPLATE = """
====================================================================
  HUMAN REVIEW REQUIRED
====================================================================

The Solution Architect has produced a design. Please review before
code generation begins.

---- PROJECT ---------------------------------------------------
  Name       : {project_name}
  Namespace  : {namespace}
  Template   : {template_type}
  Complexity : {complexity}
  HITL reason: {hitl_reason}

---- CODED ACTIVITIES TO GENERATE ------------------------------
{activities_list}

---- CONFIG KEYS -----------------------------------------------
{config_keys}

---- NUGET PACKAGES --------------------------------------------
{nuget_packages}

----------------------------------------------------------------
Options:
  - "approved"           -> proceed with this design
  - "rejected: reason"   -> abort generation
----------------------------------------------------------------
"""


def format_hitl_display(sdd: dict) -> str:
    """Format the SDD for human-readable display in the terminal."""
    activities = sdd.get("coded_activities", [])
    activities_list = "\n".join([
        f"  - {ca.get('class_name', '?')}: {ca.get('purpose', '')}"
        for ca in activities
    ]) or "  (none)"

    config_keys = "\n".join([
        f"  - {ck.get('key', '?')}: {ck.get('description', '')}"
        for ck in sdd.get("config_keys", [])
    ]) or "  (none)"

    nuget_packages = "\n".join([
        f"  - {pkg}" for pkg in sdd.get("nuget_packages", [])
    ]) or "  (none)"

    return HITL_DISPLAY_TEMPLATE.format(
        project_name=sdd.get("project_name", "TBD"),
        namespace=sdd.get("namespace", "TBD"),
        template_type=sdd.get("template_type", "TBD"),
        complexity=sdd.get("complexity", "TBD"),
        hitl_reason=sdd.get("hitl_reason", "Complex design - review recommended"),
        activities_list=activities_list,
        config_keys=config_keys,
        nuget_packages=nuget_packages,
    )


async def hitl_node(state: ProjectState) -> dict:
    """
    HITL review node.

    This node runs AFTER the graph is resumed from an interrupt.
    The last HumanMessage in state contains the user's review response.

    For simple CLI usage without interrupt_before, this node reads
    the last human message and processes approval/rejection.
    """
    sdd = state.get("sdd", {})

    # Find the human's review response (last human message)
    human_response = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            human_response = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "user":
            human_response = msg.get("content", "")
            break

    if not human_response:
        # No response yet - display the SDD for review
        display = format_hitl_display(sdd)
        return {
            "messages": [AIMessage(content=display)],
            "current_phase": "hitl",
        }

    response_lower = human_response.strip().lower()

    if response_lower.startswith("approved"):
        return {
            "messages": [AIMessage(content="HITL approved. Proceeding to code generation.")],
            "hitl_approved": True,
            "current_phase": "hitl",
        }
    elif response_lower.startswith("rejected"):
        reason = human_response[8:].strip(": ").strip() or "No reason provided"
        return {
            "messages": [AIMessage(content=f"Build rejected: {reason}")],
            "hitl_approved": False,
            "hitl_feedback": reason,
            "current_phase": "hitl",
        }
    else:
        # Treat ambiguous as rejection for safety
        return {
            "messages": [AIMessage(content=f"Unclear response: '{human_response[:100]}'. Treating as rejection.")],
            "hitl_approved": False,
            "hitl_feedback": human_response,
            "current_phase": "hitl",
        }
