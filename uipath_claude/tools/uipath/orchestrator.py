"""UiPath Orchestrator API tool."""
from langchain_core.tools import tool


@tool
def orchestrator_api_tool(endpoint: str, method: str = "GET") -> str:
    """
    Call UiPath Orchestrator API.
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        
    Returns:
        API response
    """
    # TODO: Implement Orchestrator API calls
    return f"Orchestrator API: {method} {endpoint}"
