"""CLI utility functions."""
from typing import Tuple, List, Optional


def parse_slash_command(user_input: str) -> Tuple[Optional[str], List[str]]:
    """
    Parse slash command from user input.
    
    Args:
        user_input: User input string
        
    Returns:
        Tuple of (command_name, arguments) or (None, []) if not a command
    """
    if not user_input.startswith("/"):
        return None, []
    
    parts = user_input[1:].split()
    if not parts:
        return None, []
    
    command = parts[0]
    args = parts[1:]
    
    return command, args
