"""Tool orchestration for conversation engine."""
from typing import List, Any, Callable


class ToolOrchestrator:
    """Orchestrates tool selection and execution."""
    
    def __init__(self, tools: List[Any]):
        """
        Initialize tool orchestrator.
        
        Args:
            tools: List of available tools
        """
        self.tools = tools
    
    def add_tool(self, tool: Callable) -> None:
        """
        Add a tool to the orchestrator.
        
        Args:
            tool: Tool function
        """
        self.tools.append(tool)
    
    def get_tools(self) -> List[Any]:
        """
        Get all available tools.
        
        Returns:
            List of tools
        """
        return self.tools
