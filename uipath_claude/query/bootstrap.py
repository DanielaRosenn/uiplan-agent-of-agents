"""Bootstrap flow orchestration (BA -> SA -> Developer -> QA)."""
from typing import Dict, Any
from uipath_claude.agents.ba import BAAgent
from uipath_claude.agents.sa import SAAgent
from uipath_claude.agents.developer import DeveloperAgent
from uipath_claude.agents.qa import QAAgent


async def run_bootstrap_flow(user_request: str) -> Dict[str, Any]:
    """
    Run the bootstrap flow through all agent stages.
    
    Args:
        user_request: Initial user request
        
    Returns:
        Dictionary with outputs from each stage
    """
    ba = BAAgent()
    pdd = await ba.run(user_request)
    
    sa = SAAgent()
    sdd = await sa.run(f"Create SDD based on this PDD:\n\n{pdd}")
    
    dev = DeveloperAgent()
    code = await dev.run(f"Implement based on:\n\nPDD:\n{pdd}\n\nSDD:\n{sdd}")
    
    qa = QAAgent()
    validation = await qa.run(f"Validate this implementation:\n\n{code}")
    
    return {
        "pdd": pdd,
        "sdd": sdd,
        "code": code,
        "validation": validation,
    }
