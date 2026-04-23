"""Base agent class."""
from typing import List


class BaseAgent:
    """Base class for all agents."""
    
    def __init__(self, role: str, system_prompt: str, skills: List[str]):
        """
        Initialize base agent.
        
        Args:
            role: Agent role identifier
            system_prompt: System prompt for the agent
            skills: List of skill names available to this agent
        """
        self.role = role
        self.system_prompt = system_prompt
        self.skills = skills
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        
        Returns:
            System prompt string
        """
        return self.system_prompt
    
    async def run(self, user_input: str) -> str:
        """
        Run the agent with user input.
        
        Args:
            user_input: User message
            
        Returns:
            Agent response
        """
        return f"[{self.role}] Processing: {user_input}"
