"""Skill tool creation."""
from typing import Dict, Any
from langchain_core.tools import tool
from uipath_claude.skills.loader import load_skill_content


def create_skill_tool(skill_metadata: Dict[str, Any]):
    """
    Create a LangChain tool from skill metadata.
    
    Args:
        skill_metadata: Skill metadata dictionary
        
    Returns:
        LangChain tool
    """
    skill_name = skill_metadata["name"]
    skill_description = skill_metadata["description"]
    skill_path = skill_metadata.get("path", "")
    
    @tool
    def skill_tool(query: str) -> str:
        """Execute skill with given query."""
        content = load_skill_content(skill_path)
        return f"Skill: {skill_name}\n\nContent:\n{content}\n\nQuery: {query}"
    
    # Set name and description after creation
    skill_tool.name = skill_name
    skill_tool.description = skill_description
    
    return skill_tool
