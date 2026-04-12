"""UiPath Ask AI tool."""
import os

import httpx
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
    endpoint = os.getenv("UIPATH_ASKAI_ENDPOINT", "").strip()
    api_key = os.getenv("UIPATH_ASKAI_API_KEY", "").strip()
    if not endpoint:
        return (
            "AskAI is not configured. Set UIPATH_ASKAI_ENDPOINT "
            "(and UIPATH_ASKAI_API_KEY if required)."
        )

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    payload = {"query": query}
    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        return str(data.get("answer") or data.get("result") or data)
    except Exception as exc:
        return f"AskAI request failed: {exc}"
