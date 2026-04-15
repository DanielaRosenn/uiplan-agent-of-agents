"""Tool for managing skill insights - runtime learning about skills."""
from pathlib import Path
from typing import Optional, Dict, Any, List

from uipath_claude.skills.insights import (
    SkillInsight,
    SkillInsightsStore,
    InsightType,
    InsightLayer,
)


class SkillInsightsTool:
    """
    Tool for agent to explicitly record or query insights about skills.
    
    Actions:
      - add: Record a new insight about a skill
      - query: Get existing insights for a skill  
      - propose: Suggest an improvement to the skill (stored for human review)
      - stats: Get usage statistics for a skill
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.store = SkillInsightsStore(self.project_root)
    
    def __call__(
        self,
        action: str,
        skill_name: str,
        insight_type: Optional[str] = None,
        content: Optional[str] = None,
        context: Optional[str] = None,
        layer: str = "project",
    ) -> Dict[str, Any]:
        """
        Manage skill insights.
        
        Args:
            action: One of "add", "query", "propose", "stats"
            skill_name: Name of the skill
            insight_type: Type of insight (for add/propose): success_pattern, 
                         failure_pattern, edge_case, gotcha, improvement, context_tip
            content: Content of the insight (for add/propose)
            context: Optional context about when this insight was learned
            layer: Storage layer: "user", "project", or "shared"
            
        Returns:
            Result dictionary with action-specific data
        """
        if action == "add":
            return self._add_insight(skill_name, insight_type, content, context, layer)
        elif action == "query":
            return self._query_insights(skill_name)
        elif action == "propose":
            return self._propose_insight(skill_name, insight_type, content, context)
        elif action == "stats":
            return self._get_stats(skill_name)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. Valid actions: add, query, propose, stats",
            }
    
    def _add_insight(
        self,
        skill_name: str,
        insight_type: Optional[str],
        content: Optional[str],
        context: Optional[str],
        layer_str: str,
    ) -> Dict[str, Any]:
        """Add a new insight about a skill."""
        if not insight_type:
            return {"success": False, "error": "insight_type is required for add action"}
        if not content:
            return {"success": False, "error": "content is required for add action"}
        
        try:
            itype = InsightType(insight_type)
        except ValueError:
            valid = [t.value for t in InsightType]
            return {"success": False, "error": f"Invalid insight_type. Valid: {valid}"}
        
        try:
            layer = InsightLayer(layer_str)
        except ValueError:
            valid = [l.value for l in InsightLayer]
            return {"success": False, "error": f"Invalid layer. Valid: {valid}"}
        
        insight = SkillInsight(
            skill_name=skill_name,
            insight_type=itype,
            content=content,
            context=context,
            source="agent",
        )
        
        added = self.store.add_insight(insight, layer)
        
        if added:
            return {
                "success": True,
                "message": f"Added {insight_type} insight for {skill_name}",
                "content_hash": insight.content_hash,
            }
        else:
            return {
                "success": False,
                "error": "Duplicate insight - similar content already exists",
            }
    
    def _query_insights(self, skill_name: str) -> Dict[str, Any]:
        """Query existing insights for a skill."""
        insights = self.store.get_insights(skill_name)
        summary = self.store.get_summary(skill_name)
        
        return {
            "success": True,
            "skill_name": skill_name,
            "total_insights": len(insights),
            "insights": [
                {
                    "type": i.insight_type.value,
                    "content": i.content,
                    "confidence": i.confidence,
                    "source": i.source,
                }
                for i in insights
            ],
            "summary": summary,
        }
    
    def _propose_insight(
        self,
        skill_name: str,
        insight_type: Optional[str],
        content: Optional[str],
        context: Optional[str],
    ) -> Dict[str, Any]:
        """Propose an insight for human review."""
        if not content:
            return {"success": False, "error": "content is required for propose action"}
        
        # Default to improvement type for proposals
        itype = InsightType.IMPROVEMENT
        if insight_type:
            try:
                itype = InsightType(insight_type)
            except ValueError:
                pass
        
        insight = SkillInsight(
            skill_name=skill_name,
            insight_type=itype,
            content=content,
            context=context,
            source="proposal",
        )
        
        path = self.store.propose_insight(insight)
        
        return {
            "success": True,
            "message": f"Proposal saved for human review",
            "skill_name": skill_name,
            "proposal_path": str(path),
        }
    
    def _get_stats(self, skill_name: str) -> Dict[str, Any]:
        """Get statistics for a skill."""
        insights = self.store.get_insights(skill_name)
        
        if not insights:
            return {
                "success": True,
                "skill_name": skill_name,
                "total_insights": 0,
                "message": "No insights recorded for this skill",
            }
        
        # Calculate stats
        by_type: Dict[str, int] = {}
        total_success = 0
        total_failure = 0
        
        for insight in insights:
            t = insight.insight_type.value
            by_type[t] = by_type.get(t, 0) + 1
            total_success += insight.success_count
            total_failure += insight.failure_count
        
        total_uses = total_success + total_failure
        
        return {
            "success": True,
            "skill_name": skill_name,
            "total_insights": len(insights),
            "total_uses": total_uses,
            "success_rate": total_success / total_uses if total_uses > 0 else None,
            "by_type": by_type,
            "avg_confidence": sum(i.confidence for i in insights) / len(insights),
        }


def skill_insights_tool(
    action: str,
    skill_name: str,
    insight_type: Optional[str] = None,
    content: Optional[str] = None,
    context: Optional[str] = None,
    layer: str = "project",
) -> Dict[str, Any]:
    """
    Manage skill insights - record, query, or propose learnings about skills.
    
    This tool allows the agent to:
    - Record what worked or failed when using a skill
    - Query existing knowledge about a skill before using it
    - Propose improvements to skills for human review
    
    Args:
        action: One of:
            - "add": Record a new insight
            - "query": Get existing insights for a skill
            - "propose": Suggest a skill improvement (for human review)
            - "stats": Get usage statistics
        skill_name: Name of the skill (e.g., "uipath-cli-git")
        insight_type: Type of insight (required for add/propose):
            - "success_pattern": What worked well
            - "failure_pattern": What failed and why
            - "edge_case": Non-obvious scenario
            - "gotcha": Common mistake to avoid
            - "improvement": Suggested enhancement
            - "context_tip": When to use/not use
        content: The insight content (required for add/propose)
        context: Optional context about when this was learned
        layer: Where to store (default "project"):
            - "user": Personal (~/.cursor/skill-insights/)
            - "project": Team (.uipath-claude/skill-insights/)
            - "shared": Curated (extensions/skill-insights/) - use propose instead
    
    Returns:
        Result dictionary with success status and relevant data
        
    Examples:
        # Record a gotcha
        skill_insights_tool(
            action="add",
            skill_name="uipath-cli-git",
            insight_type="gotcha",
            content="Close Studio before running studio package analyze"
        )
        
        # Query what's known about a skill
        skill_insights_tool(action="query", skill_name="uipath-rpa")
        
        # Propose improvement for human review
        skill_insights_tool(
            action="propose",
            skill_name="uipath-reframework",
            content="Add section on handling transient network errors"
        )
    """
    tool = SkillInsightsTool()
    return tool(action, skill_name, insight_type, content, context, layer)
