"""Test base agent."""
from uipath_claude.agents.base import BaseAgent


def test_base_agent_creation():
    """Test creating a base agent."""
    agent = BaseAgent(
        role="test",
        system_prompt="You are a test agent.",
        skills=["test-skill"],
    )
    
    assert agent.role == "test"
    assert agent.system_prompt == "You are a test agent."
    assert agent.skills == ["test-skill"]


def test_base_agent_get_system_prompt():
    """Test getting system prompt."""
    agent = BaseAgent(
        role="test",
        system_prompt="Test prompt.",
        skills=[],
    )
    
    prompt = agent.get_system_prompt()
    assert "Test prompt" in prompt
