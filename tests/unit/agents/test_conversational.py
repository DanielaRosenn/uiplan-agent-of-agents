"""Test conversational agent."""
from uipath_claude.agents.conversational import ConversationalAgent


def test_conversational_agent_creation():
    """Test creating conversational agent."""
    agent = ConversationalAgent()
    
    assert agent.role == "conversational"
    assert "assistant" in agent.system_prompt.lower() or "helpful" in agent.system_prompt.lower()
    assert agent.skills == ["*"]
