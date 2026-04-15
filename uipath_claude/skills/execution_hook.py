"""Post-skill-execution hook for automatic insight capture."""
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from uipath_claude.skills.insights import (
    SkillInsight,
    SkillInsightsStore,
    InsightType,
    InsightLayer,
)
from uipath_claude.skills.usage_tracker import (
    SkillUsageTracker,
    SkillUsageEvent,
    UsageTrackerConfig,
    create_usage_tracker,
)


class SkillExecutionContext:
    """
    Context manager for tracking skill execution.
    
    Usage:
        with SkillExecutionContext("uipath-cli-git") as ctx:
            # Execute skill...
            ctx.add_tool_call()
            ctx.add_tool_call()
            if error:
                ctx.set_error("Error message")
            ctx.set_context("What was being attempted")
    """
    
    def __init__(
        self,
        skill_name: str,
        tracker: Optional[SkillUsageTracker] = None,
        insights_used: Optional[List[str]] = None,
    ):
        self.skill_name = skill_name
        self.tracker = tracker or create_usage_tracker()
        self.started_at = datetime.utcnow().isoformat() + "Z"
        self.tool_calls = 0
        self.error_message: Optional[str] = None
        self.context_summary: Optional[str] = None
        self.insights_used = insights_used or []
        self._captured_insight: Optional[SkillInsight] = None
    
    def __enter__(self) -> "SkillExecutionContext":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        ended_at = datetime.utcnow().isoformat() + "Z"
        success = exc_type is None and self.error_message is None
        
        if exc_val:
            self.error_message = str(exc_val)[:500]
        
        event = SkillUsageEvent(
            skill_name=self.skill_name,
            started_at=self.started_at,
            ended_at=ended_at,
            success=success,
            tool_calls=self.tool_calls,
            error_message=self.error_message,
            context_summary=self.context_summary,
            insights_used=self.insights_used,
        )
        
        self._captured_insight = self.tracker.record_usage(event)
        return False
    
    def add_tool_call(self) -> None:
        """Increment tool call counter."""
        self.tool_calls += 1
    
    def set_error(self, error: str) -> None:
        """Set error message (marks execution as failed)."""
        self.error_message = error[:500] if error else None
    
    def set_context(self, context: str) -> None:
        """Set context summary for insight capture."""
        self.context_summary = context[:500] if context else None
    
    def mark_insight_used(self, content_hash: str) -> None:
        """Mark that an insight was used during this execution."""
        if content_hash not in self.insights_used:
            self.insights_used.append(content_hash)
    
    @property
    def captured_insight(self) -> Optional[SkillInsight]:
        """Get the insight that was auto-captured, if any."""
        return self._captured_insight


def post_skill_execution_hook(
    skill_name: str,
    success: bool,
    tool_calls: int,
    error: Optional[str] = None,
    context: Optional[str] = None,
    insights_used: Optional[List[str]] = None,
    tracker: Optional[SkillUsageTracker] = None,
) -> Optional[SkillInsight]:
    """
    Called after skill execution to potentially capture insights.
    
    Auto-capture rules:
    - Failure: always capture as failure_pattern
    - Success after 5+ tool calls: capture as edge_case (complex workflow)
    - Success after previous failure: capture as success_pattern
    
    Args:
        skill_name: Name of the skill that was executed
        success: Whether execution succeeded
        tool_calls: Number of tool calls made during execution
        error: Error message if failed
        context: Brief summary of what was attempted
        insights_used: Content hashes of insights that were in context
        tracker: Optional tracker instance (creates new one if not provided)
        
    Returns:
        SkillInsight if one was auto-captured, None otherwise
    """
    tracker = tracker or create_usage_tracker()
    
    event = SkillUsageEvent(
        skill_name=skill_name,
        started_at=datetime.utcnow().isoformat() + "Z",
        ended_at=datetime.utcnow().isoformat() + "Z",
        success=success,
        tool_calls=tool_calls,
        error_message=error[:500] if error else None,
        context_summary=context[:500] if context else None,
        insights_used=insights_used or [],
    )
    
    return tracker.record_usage(event)


class SkillExecutionHooks:
    """
    Registry for skill execution hooks.
    
    Allows registering callbacks that run before/after skill execution.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.tracker = create_usage_tracker(self.project_root)
        self._pre_hooks: List[Callable[[str], None]] = []
        self._post_hooks: List[Callable[[SkillUsageEvent, Optional[SkillInsight]], None]] = []
    
    def register_pre_hook(self, hook: Callable[[str], None]) -> None:
        """Register a hook to run before skill execution."""
        self._pre_hooks.append(hook)
    
    def register_post_hook(
        self,
        hook: Callable[[SkillUsageEvent, Optional[SkillInsight]], None],
    ) -> None:
        """Register a hook to run after skill execution."""
        self._post_hooks.append(hook)
    
    def create_context(
        self,
        skill_name: str,
        insights_used: Optional[List[str]] = None,
    ) -> SkillExecutionContext:
        """
        Create an execution context for a skill.
        
        Args:
            skill_name: Name of the skill being executed
            insights_used: Content hashes of insights in the context
            
        Returns:
            SkillExecutionContext to use with 'with' statement
        """
        for hook in self._pre_hooks:
            try:
                hook(skill_name)
            except Exception:
                pass
        
        ctx = SkillExecutionContext(
            skill_name=skill_name,
            tracker=self.tracker,
            insights_used=insights_used,
        )
        
        return ctx
    
    def notify_post_hooks(
        self,
        event: SkillUsageEvent,
        insight: Optional[SkillInsight],
    ) -> None:
        """Notify all post-execution hooks."""
        for hook in self._post_hooks:
            try:
                hook(event, insight)
            except Exception:
                pass
    
    def get_insights_summary(self, skill_name: str, max_tokens: int = 200) -> str:
        """
        Get insights summary for a skill to inject into context.
        
        Args:
            skill_name: Name of the skill
            max_tokens: Token budget for summary
            
        Returns:
            Markdown summary of insights
        """
        return self.tracker.insights_store.get_summary(skill_name, max_tokens)


_global_hooks: Optional[SkillExecutionHooks] = None


def get_execution_hooks(project_root: Optional[Path] = None) -> SkillExecutionHooks:
    """Get or create the global execution hooks instance."""
    global _global_hooks
    if _global_hooks is None:
        _global_hooks = SkillExecutionHooks(project_root)
    return _global_hooks


def track_skill_execution(
    skill_name: str,
    insights_used: Optional[List[str]] = None,
) -> SkillExecutionContext:
    """
    Convenience function to track skill execution.
    
    Usage:
        with track_skill_execution("uipath-cli-git") as ctx:
            # Execute skill...
            ctx.add_tool_call()
    """
    hooks = get_execution_hooks()
    return hooks.create_context(skill_name, insights_used)
