"""QA agent."""
from uipath_claude.agents.base import BaseAgent


class QAAgent(BaseAgent):
    """QA agent for testing and validation."""
    
    def __init__(self):
        """Initialize QA agent."""
        super().__init__(
            role="qa",
            system_prompt="""You are a QA Engineer for UiPath automation projects.

Your responsibilities:
- Review code quality and best practices
- Generate test cases and test data
- Execute tests and report issues
- Validate workflows against requirements

Available skills: Code review, test generation, live UI interaction testing, Jira integration.""",
            skills=[
                "uipath-code-reviewer",
                "uipath-test-generator",
                "uipath-interact",
                "uipath-report-issue",
                "uipath-jira-connector",
                "uipath-platform",
            ],
        )
