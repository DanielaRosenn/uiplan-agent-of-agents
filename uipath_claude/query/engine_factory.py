"""Create ConversationEngine from environment."""
import os

from uipath_claude.query.conversation import ConversationEngine


def create_conversation_engine_from_env(
    *, task_id: str = "conversation"
) -> ConversationEngine:
    """Build Bedrock engine; model id is resolved lazily by the routing helper."""
    region = os.getenv("AWS_REGION", "us-east-1")
    return ConversationEngine(model_name=None, region=region, task_id=task_id)
