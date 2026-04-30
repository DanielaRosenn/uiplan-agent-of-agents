"""Skill registry with multi-source loading, filtering, and provenance tracking."""
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from uipath_claude.skills.discovery import discover_skills
from uipath_claude.skills.sources import build_skill_sources, SkillOrigin
from uipath_claude.skills.updater import get_current_commit, get_skills_submodule_path


# Agent-specific skill filters (based on UiPath/skills repo)
AGENT_SKILLS = {
    "ba": [
        "uipath-planner",
        "uipath-human-in-the-loop",
        "uipath-platform",
        "uipath-feedback",
    ],
    "sa": [
        "uipath-planner",
        "uipath-maestro-flow",
        "uipath-platform",
        "uipath-diagnostics",
    ],
    "developer": [
        "uipath-planner",
        "uipath-rpa",
        "uipath-agents",
        "uipath-coded-apps",
        "uipath-interact",
        "uipath-platform",
        "uipath-diagnostics",
        "uipath-feedback",
    ],
    "qa": [
        "uipath-interact",
        "uipath-diagnostics",
        "uipath-feedback",
        "uipath-platform",
    ],
    "conversational": ["*"],
}


class SkillRegistry:
    """Registry for managing skills from multiple sources with provenance tracking."""
    
    def __init__(
        self,
        sources: Optional[Union[List[str], List[tuple[str, SkillOrigin]]]] = None,
        project_root: Optional[Path] = None,
    ):
        """
        Initialize skill registry.
        
        Args:
            sources: List of directory paths or (path, origin) tuples to search for skills.
                     If None, uses build_skill_sources() with project_root.
            project_root: Root path for the project. Defaults to cwd.
        """
        self.project_root = project_root or Path.cwd()
        
        if sources is None:
            self.sources = build_skill_sources(self.project_root)
        elif sources and isinstance(sources[0], tuple):
            self.sources = sources
        else:
            # Legacy: list of strings without origin - assume PROJECT
            self.sources = [(s, SkillOrigin.PROJECT) for s in sources]
        
        self.skills: List[Dict[str, Any]] = []
    
    def load_skills(self) -> List[Dict[str, Any]]:
        """
        Load skills from all sources with deduplication and provenance tracking.
        
        Each skill gets:
          - source_root: filesystem path to the source directory
          - origin: SkillOrigin value (user, extensions, uipath-submodule, etc.)
        
        First source wins: if user has skill-x, UiPath's skill-x is ignored.
        
        Returns:
            List of unique skills (first source wins for duplicates)
        """
        self.skills = []
        seen_names: set[str] = set()
        
        for source_path, origin in self.sources:
            discovered = discover_skills(source_path)
            
            for skill in discovered:
                name = skill["name"]
                if name not in seen_names:
                    skill["source_root"] = str(source_path)
                    skill["origin"] = origin.value
                    self.skills.append(skill)
                    seen_names.add(name)
        
        return self.skills
    
    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific skill by name.
        
        Args:
            skill_name: Name of the skill to retrieve
            
        Returns:
            Skill dict if found, None otherwise
        """
        for skill in self.skills:
            if skill["name"] == skill_name:
                return skill
        return None
    
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
    
    def filter_by_origin(self, origin: SkillOrigin) -> List[Dict[str, Any]]:
        """
        Filter skills by their origin/provenance.
        
        Args:
            origin: SkillOrigin to filter by
            
        Returns:
            List of skills from the specified origin
        """
        return [s for s in self.skills if s.get("origin") == origin.value]
    
    def generate_manifest(self) -> Dict[str, Any]:
        """
        Generate skills manifest for auditing and CI.
        
        Returns dict with:
          - generated_at: ISO timestamp
          - submodule_commit: current commit of skills/ submodule (for traceability)
          - skills: list of {name, origin, path, description} for every loaded skill
          - by_origin: skills grouped by origin (easy to see "what's ours vs official")
          - counts: summary counts by origin
        """
        # Get submodule commit if available
        try:
            submodule_commit = get_current_commit(get_skills_submodule_path())
        except Exception:
            submodule_commit = None
        
        # Group skills by origin
        by_origin: Dict[str, List[str]] = {origin.value: [] for origin in SkillOrigin}
        for skill in self.skills:
            origin = skill.get("origin", "unknown")
            if origin in by_origin:
                by_origin[origin].append(skill["name"])
            else:
                by_origin[origin] = [skill["name"]]
        
        # Build counts
        counts = {origin: len(names) for origin, names in by_origin.items() if names}
        
        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "submodule_commit": submodule_commit,
            "total_skills": len(self.skills),
            "counts": counts,
            "skills": [
                {
                    "name": s["name"],
                    "origin": s.get("origin", "unknown"),
                    "path": s.get("path", ""),
                    "description": s.get("description", "")[:200],
                }
                for s in self.skills
            ],
            "by_origin": by_origin,
        }
