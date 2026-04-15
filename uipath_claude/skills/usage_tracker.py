"""Skill usage tracking and automatic insight capture."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from uipath_claude.skills.insights import (
    SkillInsight,
    SkillInsightsStore,
    InsightType,
    InsightLayer,
)


@dataclass
class SkillUsageEvent:
    """
    A single skill usage for tracking.
    
    Captured automatically by post-execution hook.
    """
    skill_name: str
    started_at: str
    ended_at: str
    success: bool
    tool_calls: int
    error_message: Optional[str] = None
    context_summary: Optional[str] = None
    insights_used: List[str] = field(default_factory=list)


@dataclass
class UsageTrackerConfig:
    """Configuration for the usage tracker."""
    enabled: bool = True
    auto_capture_on_failure: bool = True
    auto_capture_on_complex_success: bool = True
    complexity_threshold: int = 5
    auto_capture_on_recovery: bool = True
    default_layer: InsightLayer = InsightLayer.PROJECT
    min_confidence: float = 0.3


class SkillUsageTracker:
    """
    Tracks skill usage and triggers insight capture.
    
    Auto-capture rules:
    - On failure: always capture error context as 'failure_pattern'
    - On success after previous failure: capture as 'success_pattern'
    - On success with 5+ tool calls: capture as 'edge_case' (complex workflow)
    """
    
    def __init__(
        self,
        insights_store: SkillInsightsStore,
        config: Optional[UsageTrackerConfig] = None,
    ):
        self.insights_store = insights_store
        self.config = config or UsageTrackerConfig()
        self.current_session: Dict[str, List[SkillUsageEvent]] = {}
        self._insight_callbacks: List[Callable[[SkillInsight], None]] = []
    
    def on_insight_captured(self, callback: Callable[[SkillInsight], None]) -> None:
        """Register a callback for when insights are captured."""
        self._insight_callbacks.append(callback)
    
    def _notify_insight_captured(self, insight: SkillInsight) -> None:
        """Notify all registered callbacks about a captured insight."""
        for callback in self._insight_callbacks:
            try:
                callback(insight)
            except Exception:
                pass
    
    def record_usage(self, event: SkillUsageEvent) -> Optional[SkillInsight]:
        """
        Record a skill usage event and maybe auto-capture insight.
        
        Args:
            event: The usage event to record
            
        Returns:
            SkillInsight if one was auto-captured, None otherwise
        """
        if not self.config.enabled:
            return None
        
        # Track in session
        if event.skill_name not in self.current_session:
            self.current_session[event.skill_name] = []
        self.current_session[event.skill_name].append(event)
        
        # Check auto-capture rules
        insight = self._check_auto_capture(event)
        if insight:
            self.insights_store.add_insight(insight, self.config.default_layer)
            self._notify_insight_captured(insight)
        
        # Update insight stats if insights were used
        for insight_hash in event.insights_used:
            self.insights_store.update_insight_stats(
                event.skill_name,
                insight_hash,
                success=event.success,
                layer=self.config.default_layer,
            )
        
        return insight
    
    def _check_auto_capture(self, event: SkillUsageEvent) -> Optional[SkillInsight]:
        """
        Check if this event should trigger auto-capture.
        
        Returns:
            SkillInsight if capture triggered, None otherwise
        """
        # Rule 1: Capture failures
        if not event.success and self.config.auto_capture_on_failure:
            return self._create_failure_insight(event)
        
        if event.success:
            # Rule 2: Capture recovery (success after failure)
            if self.config.auto_capture_on_recovery:
                history = self.current_session.get(event.skill_name, [])
                recent_failure = any(
                    not e.success for e in history[-5:-1]
                ) if len(history) > 1 else False
                if recent_failure:
                    return self._create_recovery_insight(event)
            
            # Rule 3: Capture complex success
            if (
                self.config.auto_capture_on_complex_success
                and event.tool_calls >= self.config.complexity_threshold
            ):
                return self._create_complex_success_insight(event)
        
        return None
    
    def _create_failure_insight(self, event: SkillUsageEvent) -> SkillInsight:
        """Create a failure_pattern insight from an event."""
        content = f"{event.skill_name} failed"
        if event.error_message:
            error_preview = event.error_message[:200]
            content = f"Failure: {error_preview}"
        
        return SkillInsight(
            skill_name=event.skill_name,
            insight_type=InsightType.FAILURE_PATTERN,
            content=content,
            context=event.context_summary,
            source="auto",
        )
    
    def _create_recovery_insight(self, event: SkillUsageEvent) -> SkillInsight:
        """Create a success_pattern insight from a recovery event."""
        content = "Recovery approach"
        if event.context_summary:
            content = f"What worked: {event.context_summary[:200]}"
        
        return SkillInsight(
            skill_name=event.skill_name,
            insight_type=InsightType.SUCCESS_PATTERN,
            content=content,
            context=f"Recovered after {event.tool_calls} tool calls",
            source="auto",
        )
    
    def _create_complex_success_insight(self, event: SkillUsageEvent) -> SkillInsight:
        """Create an edge_case insight from a complex success event."""
        content = f"Complex workflow ({event.tool_calls} steps)"
        if event.context_summary:
            content = f"Complex workflow: {event.context_summary[:200]}"
        
        return SkillInsight(
            skill_name=event.skill_name,
            insight_type=InsightType.EDGE_CASE,
            content=content,
            context=f"Required {event.tool_calls} tool calls",
            source="auto",
        )
    
    def get_skill_stats(self, skill_name: str) -> Dict[str, Any]:
        """
        Get usage stats for a skill from current session.
        
        Returns dict with:
          - total_uses: int
          - success_rate: float
          - avg_tool_calls: float
          - common_errors: list[str]
        """
        events = self.current_session.get(skill_name, [])
        if not events:
            return {
                "total_uses": 0,
                "success_rate": None,
                "avg_tool_calls": None,
                "common_errors": [],
            }
        
        successes = sum(1 for e in events if e.success)
        total_tools = sum(e.tool_calls for e in events)
        
        # Collect unique error messages
        errors: Dict[str, int] = {}
        for e in events:
            if e.error_message:
                key = e.error_message[:100]
                errors[key] = errors.get(key, 0) + 1
        
        common_errors = sorted(errors.keys(), key=lambda k: -errors[k])[:5]
        
        return {
            "total_uses": len(events),
            "success_rate": successes / len(events),
            "avg_tool_calls": total_tools / len(events),
            "common_errors": common_errors,
        }
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of all skill usage in current session."""
        summary = {
            "skills_used": len(self.current_session),
            "total_events": sum(len(e) for e in self.current_session.values()),
            "by_skill": {},
        }
        
        for skill_name in self.current_session:
            summary["by_skill"][skill_name] = self.get_skill_stats(skill_name)
        
        return summary
    
    def clear_session(self) -> None:
        """Clear current session data."""
        self.current_session.clear()


def create_usage_tracker(project_root: Optional[Path] = None) -> SkillUsageTracker:
    """
    Create a SkillUsageTracker with default configuration.
    
    Args:
        project_root: Root path for the project. Defaults to cwd.
        
    Returns:
        Configured SkillUsageTracker instance
    """
    root = project_root or Path.cwd()
    store = SkillInsightsStore(root)
    return SkillUsageTracker(store)
