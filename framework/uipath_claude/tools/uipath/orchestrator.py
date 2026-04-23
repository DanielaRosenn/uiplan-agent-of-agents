"""UiPath Orchestrator API tool."""
import os

import httpx
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
    base_url = os.getenv("UIPATH_ORCHESTRATOR_URL", "").strip().rstrip("/")
    token = os.getenv("UIPATH_ORCHESTRATOR_TOKEN", "").strip()
    if not base_url or not token:
        return (
            "Orchestrator is not configured. Set UIPATH_ORCHESTRATOR_URL and "
            "UIPATH_ORCHESTRATOR_TOKEN."
        )

    url = f"{base_url}/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.request(method.upper(), url, headers=headers, timeout=30.0)
        response.raise_for_status()
        ct = response.headers.get("content-type", "")
        if "application/json" in ct:
            return str(response.json())
        return response.text
    except Exception as exc:
        return f"Orchestrator request failed: {exc}"
