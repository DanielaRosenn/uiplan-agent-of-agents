"""Create ConversationEngine from environment."""
import os

from uipath_claude.llm.router import heavy_model
from uipath_claude.query.conversation import ConversationEngine


def create_conversation_engine_from_env() -> ConversationEngine:
    """Build Bedrock engine using the HEAVY-tier model id and AWS_REGION."""
    model_name = heavy_model()
    region = os.getenv("AWS_REGION", "us-east-1")
    return ConversationEngine(model_name=model_name, region=region)
