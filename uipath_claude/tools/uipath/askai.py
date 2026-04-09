"""UiPath Ask AI tool."""
from langchain_core.tools import tool


@tool
def uipath_askai_tool(query: str) -> str:
    """
    Query UiPath documentation using Ask AI.
    
    Args:
        query: Question to ask
        
    Returns:
        Answer from UiPath docs
    """
    # TODO: Implement Ask AI integration
    return f"Ask AI: {query}"
