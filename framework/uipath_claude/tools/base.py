"""Base tool classes."""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Base class for all tools."""
    
    name: str
    description: str
    
    @abstractmethod
    def _run(self, **kwargs) -> Any:
        """
        Execute the tool.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Tool execution result
        """
        pass
