"""Business Analyst agent."""
from uipath_claude.agents.base import BaseAgent


class BAAgent(BaseAgent):
    """Business Analyst agent for PDD creation."""
    
    def __init__(self):
        """Initialize BA agent."""
        super().__init__(
            role="ba",
            system_prompt="""You are a Business Analyst for UiPath automation projects.

Your responsibilities:
- Gather requirements from stakeholders
- Create Process Definition Documents (PDDs)
- Design business process flows
- Document business rules and exceptions

Available skills: PDD creation, business flow canvas, Confluence, Jira.""",
            skills=[
                "pdd-creation",
                "business-flow-canvas",
                "uipath-confluence-connector",
                "jira-ticket-creation",
                "uipath-platform",
            ],
        )
