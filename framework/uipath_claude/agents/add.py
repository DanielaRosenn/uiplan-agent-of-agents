"""Architecture Design Document (ADD) agent."""
from uipath_claude.agents.base import BaseAgent


class ADDAgent(BaseAgent):
    """Architecture Design Document agent.

    Produces the ADD (component diagrams, integration boundaries, error
    handling, scaling) downstream of the SDD.
    """

    def __init__(self):
        super().__init__(
            role="add",
            system_prompt="""You are an Architecture Design author for UiPath automation projects.

Your responsibilities:
- Translate the SDD into a concrete Architecture Design Document (ADD)
- Define component boundaries, integration points, data flow, and contracts
- Specify error handling, retry, idempotency, and observability requirements
- Document deployment topology (folders, environments, robot types)

Output a structured markdown ADD with these sections:
1. System context (actors + integrations)
2. Component breakdown (per workflow / coded module)
3. Data + control flow
4. Error model and recovery semantics
5. Security + secrets handling
6. Deployment topology
7. Open questions / risks""",
            skills=[
                "uipath-platform",
                "uipath-rpa",
                "uipath-maestro-flow",
            ],
        )
