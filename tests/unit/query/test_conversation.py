"""Test conversation engine."""
from unittest.mock import AsyncMock, MagicMock
from uipath_claude.query.conversation import ConversationEngine


def test_conversation_engine_creation():
    """Test creating conversation engine."""
    engine = ConversationEngine(
        model_name="anthropic.claude-3-sonnet-20240229-v1:0",
        region="us-east-1",
    )
    
    assert engine.model_name == "anthropic.claude-3-sonnet-20240229-v1:0"
    assert engine.region == "us-east-1"
