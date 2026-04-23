"""Conversational agent (default mode)."""
from uipath_claude.agents.base import BaseAgent


class ConversationalAgent(BaseAgent):
    """Default conversational agent with access to all skills."""
    
    def __init__(self):
        """Initialize conversational agent."""
        super().__init__(
            role="conversational",
            system_prompt="""You are a helpful UiPath automation assistant.

You have access to all available skills and tools. Help users with:
- UiPath project development
- Workflow design and implementation
- Documentation and best practices
- Troubleshooting and debugging

Use the most appropriate skill or tool for each task.""",
            skills=["*"],
        )
