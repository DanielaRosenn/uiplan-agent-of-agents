"""Create ConversationEngine from environment."""
import os

from uipath_claude.config import DEFAULT_BEDROCK_MODEL
from uipath_claude.query.conversation import ConversationEngine


def create_conversation_engine_from_env() -> ConversationEngine:
    """Build Bedrock engine using UIPATH_CLAUDE_MODEL and AWS_REGION."""
    model_name = os.getenv("UIPATH_CLAUDE_MODEL", DEFAULT_BEDROCK_MODEL)
    region = os.getenv("AWS_REGION", "us-east-1")
    return ConversationEngine(model_name=model_name, region=region)
