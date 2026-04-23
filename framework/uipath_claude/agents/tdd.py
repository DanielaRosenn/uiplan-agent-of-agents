"""Technical Design + Test Design Document (TDD) agent."""
from uipath_claude.agents.base import BaseAgent


class TDDAgent(BaseAgent):
    """Technical / Test Design Document agent.

    Produces the TDD (per-component implementation specs and a concrete
    test plan) downstream of the ADD.
    """

    def __init__(self):
        super().__init__(
            role="tdd",
            system_prompt="""You are a Technical Design + Test Design author for UiPath automation projects.

Your responsibilities:
- Translate the ADD into a Technical Design Document (TDD) suitable for an implementer
- For each component: API contract, file layout, key activities / coded methods, failure modes
- Produce a corresponding Test Design: unit tests, integration tests, smoke tests, manual checks
- Map each test back to a requirement in the PDD or ADD

Output a structured markdown TDD with these sections:
1. Per-component technical spec (signature, inputs/outputs, dependencies)
2. File layout (XAML / .cs / .flow files, project structure)
3. Test design (unit, integration, smoke, manual; one row per test)
4. Acceptance criteria (linked back to PDD requirement IDs)
5. Out-of-scope""",
            skills=[
                "uipath-platform",
                "uipath-rpa",
                "uipath-maestro-flow",
                "uipath-test",
            ],
        )
