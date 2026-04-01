"""Tools for dynamic skill invocation."""

from pathlib import Path
import json
from typing import Optional

from langchain_core.tools import tool
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage

from agent.skill_discovery import SkillDiscovery


# Default skills path (can be overridden for testing)
SKILLS_REPO_PATH = Path(__file__).parent.parent.parent / "skills"


@tool
def get_available_skills() -> str:
    """
    Returns JSON list of all available UiPath skills with descriptions.

    Use this when you need to know what skills are available.
    Dynamically scans the cloned UiPath skills repo, so new skills
    appear automatically after repo updates.

    Returns:
        JSON string with list of skill metadata
    """
    discovery = SkillDiscovery(SKILLS_REPO_PATH)
    registry = discovery.discover_all_skills()

    skills_list = [
        {
            "name": skill.name,
            "description": skill.description,
            "triggers": skill.trigger_patterns,
            "references": [ref.name for ref in skill.references],
        }
        for skill in registry.values()
    ]

    return json.dumps(skills_list, indent=2)


@tool
def invoke_skill(
    skill_name: str,
    task_description: str,
    context: Optional[dict] = None,
) -> str:
    """
    Dynamically invoke any UiPath skill by name.

    Args:
        skill_name: Name from get_available_skills() output
        task_description: What you want the skill to do
        context: Relevant project state, files, specifications

    The skill's full SKILL.md is used as the system prompt,
    along with its references and assets available as context.

    Examples:
        invoke_skill("uipath-rpa-workflows", "Generate Main.xaml", {...})
        invoke_skill("uipath-coded-workflows", "Create activity", {...})

    Returns:
        Skill agent response
    """
    discovery = SkillDiscovery(SKILLS_REPO_PATH)
    registry = discovery.discover_all_skills()

    if skill_name not in registry:
        available = ", ".join(registry.keys())
        return f"❌ Skill '{skill_name}' not found. Available: {available}"

    skill = registry[skill_name]

    # Load skill references (truncate large docs)
    references_context = []
    for ref_path in skill.references:
        content = ref_path.read_text(encoding="utf-8")
        references_context.append({
            "file": ref_path.name,
            "content": content[:5000],  # Truncate at 5000 chars
        })

    # Build system prompt
    system_prompt = f"""
{skill.full_prompt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE REFERENCE DOCUMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{json.dumps(references_context, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT TASK REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{task_description}

Project Context:
{json.dumps(context or {}, indent=2)}
"""

    # Spawn skill agent
    skill_agent = ChatBedrockConverse(
        model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region_name="us-east-1",
        temperature=0.15,
    )

    try:
        response = skill_agent.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=task_description),
        ])
        return response.content
    except Exception as e:
        return f"❌ Skill invocation failed: {type(e).__name__}: {str(e)}\n\nThis could be due to AWS authentication, rate limits, or network issues."
