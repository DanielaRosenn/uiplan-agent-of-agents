"""Test conversation engine."""
from unittest.mock import MagicMock
from uipath_claude.query.conversation import ConversationEngine


def test_conversation_engine_creation():
    """Test creating conversation engine."""
    engine = ConversationEngine(
        model_name="anthropic.claude-3-sonnet-20240229-v1:0",
        region="us-east-1",
    )
    
    assert engine.model_name == "anthropic.claude-3-sonnet-20240229-v1:0"
    assert engine.region == "us-east-1"


class _Chunk:
    def __init__(self, content):
        self.content = content


async def _stream_chunks(_messages):
    yield _Chunk("Hello")
    yield _Chunk([{"text": " "}, {"text": "World"}])
    yield _Chunk("")


async def test_conversation_engine_run_stream_assembles_text():
    """run_stream should emit deltas and return full text."""
    engine = ConversationEngine(
        model_name="anthropic.claude-3-sonnet-20240229-v1:0",
        region="us-east-1",
    )
    fake_llm = MagicMock()
    fake_llm.astream = _stream_chunks
    engine.llm = fake_llm

    deltas: list[str] = []
    out = await engine.run_stream(
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
        system_prompt="sys",
        on_delta=deltas.append,
    )

    assert out == "Hello World"
    assert deltas == ["Hello", " ", "World"]
