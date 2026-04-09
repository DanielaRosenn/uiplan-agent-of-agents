"""Skill registry with multi-source loading and filtering."""
from typing import List, Dict, Any
from uipath_claude.skills.discovery import discover_skills


# Agent-specific skill filters
AGENT_SKILLS = {
    "ba": [
        "pdd-creation",
        "business-flow-canvas",
        "uipath-confluence-connector",
        "jira-ticket-creation",
        "uipath-platform",
    ],
    "sa": [
        "solution-canvas",
        "sdd-flow-canvas",
        "uipath-flow",
        "uipath-confluence-connector",
        "jira-ticket-creation",
        "uipath-platform",
    ],
    "developer": [
        "uipath-rpa-workflows",
        "uipath-coded-workflows",
        "uipath-coded-agents",
        "uipath-reframework",
        "uipath-longrunning-workflow",
        "uipath-jira-connector",
        "uipath-platform",
    ],
    "qa": [
        "uipath-code-reviewer",
        "uipath-test-generator",
        "uipath-servo",
        "uipath-report-issue",
        "uipath-jira-connector",
        "uipath-platform",
    ],
    "conversational": ["*"],  # All skills
}


class SkillRegistry:
    """Registry for managing skills from multiple sources."""
    
    def __init__(self, sources: List[str]):
        """
        Initialize skill registry.
        
        Args:
            sources: List of directory paths to search for skills (in priority order)
        """
        self.sources = sources
        self.skills: List[Dict[str, Any]] = []
    
    def load_skills(self) -> List[Dict[str, Any]]:
        """
        Load skills from all sources with deduplication.
        
        Returns:
            List of unique skills (first source wins for duplicates)
        """
        seen_names = set()
        
        for source in self.sources:
            discovered = discover_skills(source)
            
            for skill in discovered:
                name = skill["name"]
                if name not in seen_names:
                    self.skills.append(skill)
                    seen_names.add(name)
        
        return self.skills
    
    def filter_by_agent(self, agent_role: str) -> List[Dict[str, Any]]:
        """
        Filter skills for a specific agent role.
        
        Args:
            agent_role: Agent role ("ba", "sa", "developer", "qa", "conversational")
            
        Returns:
            List of skills available to this agent
        """
        allowed_skills = AGENT_SKILLS.get(agent_role, [])
        
        if "*" in allowed_skills:
            return self.skills
        
        return [s for s in self.skills if s["name"] in allowed_skills]
