"""UiPath Workflow Analyzer tool."""
import subprocess
from langchain_core.tools import tool


@tool
def workflow_analyzer_tool(project_path: str) -> str:
    """
    Run UiPath Workflow Analyzer on a project.
    
    Args:
        project_path: Path to UiPath project
        
    Returns:
        Analyzer results
    """
    try:
        result = subprocess.run(
            ["uipath", "studio", "package", "analyze", project_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Analyzer failed: {result.stderr}"
    
    except Exception as e:
        return f"Error running analyzer: {str(e)}"
