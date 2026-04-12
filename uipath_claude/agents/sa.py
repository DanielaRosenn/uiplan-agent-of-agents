"""Solution Architect agent."""
from uipath_claude.agents.base import BaseAgent


class SAAgent(BaseAgent):
    """Solution Architect agent for SDD creation."""
    
    def __init__(self):
        """Initialize SA agent."""
        super().__init__(
            role="sa",
            system_prompt="""You are a Solution Architect for UiPath automation projects.

Your responsibilities:
- Design technical solutions based on PDDs
- Create Solution Design Documents (SDDs)
- Define architecture and component interactions
- Document technical specifications

Available skills: SDD creation, solution canvas, UiPath flow design.""",
            skills=[
                "solution-canvas",
                "sdd-flow-canvas",
                "uipath-flow",
                "uipath-confluence-connector",
                "jira-ticket-creation",
                "uipath-platform",
            ],
        )
