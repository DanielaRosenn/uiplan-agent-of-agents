"""Developer agent."""
from uipath_claude.agents.base import BaseAgent


class DeveloperAgent(BaseAgent):
    """Developer agent for workflow implementation."""
    
    def __init__(self):
        """Initialize Developer agent."""
        super().__init__(
            role="developer",
            system_prompt="""You are a UiPath Developer.

Your responsibilities:
- Implement workflows based on SDDs
- Write XAML and coded workflows
- Follow UiPath best practices
- Integrate with Orchestrator and other services

Available skills: RPA workflows, REFramework, Long Running Workflows, coded workflows.""",
            skills=[
                "uipath-rpa-workflows",
                "uipath-coded-workflows",
                "uipath-coded-agents",
                "uipath-reframework",
                "uipath-longrunning-workflow",
                "uipath-jira-connector",
                "uipath-platform",
            ],
        )
