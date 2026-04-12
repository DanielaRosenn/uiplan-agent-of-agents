"""Command registry for slash commands."""
from typing import Dict, Callable, Any


class CommandRegistry:
    """Registry for slash commands."""
    
    def __init__(self):
        """Initialize command registry."""
        self.commands: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, description: str, handler: Callable) -> None:
        """
        Register a command.
        
        Args:
            name: Command name (without /)
            description: Command description
            handler: Command handler function
        """
        self.commands[name] = {
            "description": description,
            "handler": handler,
        }
    
    def execute(self, name: str, *args, **kwargs) -> str:
        """
        Execute a command.
        
        Args:
            name: Command name
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Command result
        """
        if name not in self.commands:
            return f"Unknown command: /{name}"
        
        handler = self.commands[name]["handler"]
        return handler(*args, **kwargs)


def register_command(registry: CommandRegistry, name: str, description: str):
    """
    Decorator for registering commands.
    
    Args:
        registry: Command registry
        name: Command name
        description: Command description
    """
    def decorator(func: Callable) -> Callable:
        registry.register(name, description, func)
        return func
    return decorator
