"""Skill insights - runtime learning about skills."""
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


class InsightType(str, Enum):
    """Types of learnings the agent can capture."""
    SUCCESS_PATTERN = "success_pattern"
    FAILURE_PATTERN = "failure_pattern"
    EDGE_CASE = "edge_case"
    GOTCHA = "gotcha"
    IMPROVEMENT = "improvement"
    CONTEXT_TIP = "context_tip"


class InsightLayer(str, Enum):
    """Storage layers for insights, in priority order."""
    USER = "user"
    PROJECT = "project"
    SHARED = "shared"


@dataclass
class SkillInsight:
    """
    A single learning about a skill.
    
    Stored in skill-insights/<skill-name>.json as append-only log.
    Periodically consolidated into summary for token efficiency.
    """
    skill_name: str
    insight_type: InsightType
    content: str
    context: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    source: str = "agent"
    success_count: int = 0
    failure_count: int = 0
    
    @property
    def confidence(self) -> float:
        """Calculate confidence score based on success/failure counts."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total
    
    @property
    def content_hash(self) -> str:
        """Hash of content for deduplication."""
        return hashlib.md5(self.content.lower().strip().encode()).hexdigest()[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d["insight_type"] = self.insight_type.value
        d["confidence"] = self.confidence
        d["content_hash"] = self.content_hash
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillInsight":
        """Create from dictionary."""
        data = data.copy()
        data.pop("confidence", None)
        data.pop("content_hash", None)
        if "insight_type" in data and isinstance(data["insight_type"], str):
            data["insight_type"] = InsightType(data["insight_type"])
        return cls(**data)


@dataclass
class SkillInsightsFile:
    """Contents of a skill insights JSON file."""
    skill_name: str
    insights: List[SkillInsight] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "skill_name": self.skill_name,
            "insights": [i.to_dict() for i in self.insights],
            "stats": self.stats,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillInsightsFile":
        """Create from dictionary."""
        return cls(
            skill_name=data.get("skill_name", ""),
            insights=[SkillInsight.from_dict(i) for i in data.get("insights", [])],
            stats=data.get("stats", {}),
        )


class SkillInsightsStore:
    """
    Layered storage for skill insights.
    
    Resolution order (first wins on conflict):
      1. User (~/.cursor/skill-insights/)
      2. Project (.uipath-claude/skill-insights/)
      3. Shared (extensions/skill-insights/)
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.layers: Dict[InsightLayer, Path] = {
            InsightLayer.USER: Path.home() / ".cursor" / "skill-insights",
            InsightLayer.PROJECT: project_root / ".uipath-claude" / "skill-insights",
            InsightLayer.SHARED: project_root / "extensions" / "skill-insights",
        }
    
    def _get_insights_path(self, skill_name: str, layer: InsightLayer) -> Path:
        """Get path to insights file for a skill in a specific layer."""
        return self.layers[layer] / f"{skill_name}.json"
    
    def _load_insights_file(self, path: Path) -> Optional[SkillInsightsFile]:
        """Load insights from a JSON file."""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return SkillInsightsFile.from_dict(data)
        except Exception:
            return None
    
    def _save_insights_file(self, path: Path, file: SkillInsightsFile) -> None:
        """Save insights to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(file.to_dict(), indent=2), encoding="utf-8")
    
    def add_insight(
        self,
        insight: SkillInsight,
        layer: InsightLayer = InsightLayer.PROJECT,
    ) -> bool:
        """
        Add insight to specified layer.
        
        Args:
            insight: The insight to add
            layer: Storage layer (user, project, shared)
            
        Returns:
            True if added, False if duplicate
        """
        path = self._get_insights_path(insight.skill_name, layer)
        file = self._load_insights_file(path) or SkillInsightsFile(
            skill_name=insight.skill_name
        )
        
        # Check for duplicates by content hash
        existing_hashes = {i.content_hash for i in file.insights}
        if insight.content_hash in existing_hashes:
            return False
        
        file.insights.append(insight)
        self._update_stats(file)
        self._save_insights_file(path, file)
        return True
    
    def _update_stats(self, file: SkillInsightsFile) -> None:
        """Update stats in an insights file."""
        total_success = sum(i.success_count for i in file.insights)
        total_failure = sum(i.failure_count for i in file.insights)
        total = total_success + total_failure
        
        file.stats = {
            "total_insights": len(file.insights),
            "total_uses": total,
            "success_rate": total_success / total if total > 0 else None,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "by_type": {},
        }
        
        for insight in file.insights:
            t = insight.insight_type.value
            file.stats["by_type"][t] = file.stats["by_type"].get(t, 0) + 1
    
    def get_insights(
        self,
        skill_name: str,
        min_confidence: float = 0.0,
    ) -> List[SkillInsight]:
        """
        Get merged insights for a skill across all layers.
        
        User insights are included first, then project, then shared.
        Deduplication by content hash (first occurrence wins).
        
        Args:
            skill_name: Name of the skill
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            
        Returns:
            List of insights, deduplicated and filtered
        """
        seen_hashes: set[str] = set()
        result: List[SkillInsight] = []
        
        for layer in InsightLayer:
            path = self._get_insights_path(skill_name, layer)
            file = self._load_insights_file(path)
            if not file:
                continue
            
            for insight in file.insights:
                if insight.content_hash in seen_hashes:
                    continue
                if insight.confidence < min_confidence:
                    continue
                seen_hashes.add(insight.content_hash)
                result.append(insight)
        
        return result
    
    def get_summary(
        self,
        skill_name: str,
        max_tokens: int = 200,
        min_confidence: float = 0.3,
    ) -> str:
        """
        Get token-efficient summary of insights for injection into context.
        
        Args:
            skill_name: Name of the skill
            max_tokens: Approximate token limit (chars / 4)
            min_confidence: Minimum confidence threshold
            
        Returns:
            Markdown snippet with insights summary
        """
        insights = self.get_insights(skill_name, min_confidence=min_confidence)
        if not insights:
            return ""
        
        # Priority order for display
        priority_order = [
            InsightType.GOTCHA,
            InsightType.FAILURE_PATTERN,
            InsightType.SUCCESS_PATTERN,
            InsightType.EDGE_CASE,
            InsightType.CONTEXT_TIP,
            InsightType.IMPROVEMENT,
        ]
        
        # Sort by priority, then by confidence
        def sort_key(i: SkillInsight) -> tuple:
            try:
                priority = priority_order.index(i.insight_type)
            except ValueError:
                priority = len(priority_order)
            return (priority, -i.confidence)
        
        insights = sorted(insights, key=sort_key)
        
        # Build summary with token budget
        max_chars = max_tokens * 4
        lines = ["## Learned from usage"]
        current_type: Optional[InsightType] = None
        char_count = len(lines[0])
        
        type_labels = {
            InsightType.GOTCHA: "**Gotchas to avoid:**",
            InsightType.FAILURE_PATTERN: "**Known failures:**",
            InsightType.SUCCESS_PATTERN: "**What works:**",
            InsightType.EDGE_CASE: "**Edge cases:**",
            InsightType.CONTEXT_TIP: "**Tips:**",
            InsightType.IMPROVEMENT: "**Suggested improvements:**",
        }
        
        for insight in insights:
            if char_count >= max_chars:
                break
            
            # Add type header if changed
            if insight.insight_type != current_type:
                label = type_labels.get(insight.insight_type, f"**{insight.insight_type.value}:**")
                if char_count + len(label) + 2 > max_chars:
                    break
                lines.append("")
                lines.append(label)
                char_count += len(label) + 2
                current_type = insight.insight_type
            
            # Add insight content
            line = f"- {insight.content}"
            if char_count + len(line) + 1 > max_chars:
                break
            lines.append(line)
            char_count += len(line) + 1
        
        # Add stats footer if space
        stats_line = f"\n*{len(insights)} insights available*"
        if char_count + len(stats_line) <= max_chars:
            lines.append(stats_line)
        
        return "\n".join(lines)
    
    def update_insight_stats(
        self,
        skill_name: str,
        content_hash: str,
        success: bool,
        layer: InsightLayer = InsightLayer.PROJECT,
    ) -> bool:
        """
        Update success/failure count for an insight.
        
        Args:
            skill_name: Name of the skill
            content_hash: Hash of the insight content to update
            success: Whether the insight helped (True) or not (False)
            layer: Which layer to update
            
        Returns:
            True if updated, False if insight not found
        """
        path = self._get_insights_path(skill_name, layer)
        file = self._load_insights_file(path)
        if not file:
            return False
        
        for insight in file.insights:
            if insight.content_hash == content_hash:
                if success:
                    insight.success_count += 1
                else:
                    insight.failure_count += 1
                self._update_stats(file)
                self._save_insights_file(path, file)
                return True
        
        return False
    
    def propose_insight(
        self,
        insight: SkillInsight,
    ) -> Path:
        """
        Propose an insight for human review (stored in proposals/).
        
        Args:
            insight: The insight to propose
            
        Returns:
            Path to the proposals file
        """
        proposals_dir = self.layers[InsightLayer.SHARED] / "proposals"
        proposals_dir.mkdir(parents=True, exist_ok=True)
        
        path = proposals_dir / f"{insight.skill_name}.json"
        file = self._load_insights_file(path) or SkillInsightsFile(
            skill_name=insight.skill_name
        )
        
        # Mark as proposal
        insight.source = "proposal"
        file.insights.append(insight)
        self._save_insights_file(path, file)
        
        return path
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get stats for all skills with insights.
        
        Returns:
            Dictionary mapping skill names to their stats
        """
        result: Dict[str, Dict[str, Any]] = {}
        
        for layer in InsightLayer:
            layer_path = self.layers[layer]
            if not layer_path.exists():
                continue
            
            for path in layer_path.glob("*.json"):
                if path.name == "proposals":
                    continue
                skill_name = path.stem
                if skill_name in result:
                    continue
                
                file = self._load_insights_file(path)
                if file and file.stats:
                    result[skill_name] = file.stats
        
        return result
