"""Skill registry with multi-source loading and filtering."""
from pathlib import Path
from typing import List, Dict, Any

from uipath_claude.skills.discovery import discover_skills
from uipath_claude.skills.sources import build_skill_sources


# Agent-specific skill filters (based on UiPath/skills repo)
AGENT_SKILLS = {
    "ba": [
        "uipath-planner",
        "uipath-human-in-the-loop",
        "uipath-case-management",
        "uipath-platform",
        "uipath-feedback",
    ],
    "sa": [
        "uipath-planner",
        "uipath-maestro-flow",
        "uipath-case-management",
        "uipath-platform",
        "uipath-diagnostics",
    ],
    "developer": [
        "uipath-planner",
        "uipath-rpa",  # Combined coded + RPA workflows
        "uipath-agents",  # Coded agents
        "uipath-coded-apps",
        "uipath-servo",  # UI automation
        "uipath-platform",
        "uipath-diagnostics",
        "uipath-feedback",
    ],
    "qa": [
        "uipath-servo",
        "uipath-diagnostics",
        "uipath-feedback",
        "uipath-platform",
    ],
    "conversational": ["*"],  # All skills
}


class SkillRegistry:
    """Registry for managing skills from multiple sources."""
    
    def __init__(self, sources: List[str] | None = None):
        """
        Initialize skill registry.
        
        Args:
            sources: List of directory paths to search for skills (in priority order)
        """
        if sources is None:
            self.sources = build_skill_sources(Path.cwd())
        else:
            self.sources = sources
        self.skills: List[Dict[str, Any]] = []
    
    def load_skills(self) -> List[Dict[str, Any]]:
        """
        Load skills from all sources with deduplication.
        
        Returns:
            List of unique skills (first source wins for duplicates)
        """
        self.skills = []
        seen_names = set()
        
        for source in self.sources:
            discovered = discover_skills(source)
            
            for skill in discovered:
                name = skill["name"]
                if name not in seen_names:
                    skill["source_root"] = str(source)
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
