"""Conversation engine for agent interactions."""
from typing import Any, Callable, Dict, List, Optional

from langchain_aws import ChatBedrockConverse  # noqa: F401  (re-exported so tests can patch)

from uipath_claude.llm.invoke import FallbackChatModel, build_chat_model
from uipath_claude.llm.routing.complexity import ComplexitySignals


class ConversationEngine:
    """Conversation engine for model-tool-model loops."""

    def __init__(
        self,
        model_name: str | None = None,
        region: str | None = None,
        *,
        task_id: str = "conversation",
    ):
        """Initialize conversation engine.

        Args:
            model_name: Optional Bedrock model ID override (legacy; routing
                helper normally resolves the model from the ``task_id`` tier).
            region: AWS region (defaults to AWS_REGION env var).
            task_id: Routing task id used by :func:`build_chat_model`.
        """
        self.model_name = model_name
        self.region = region
        self.task_id = task_id
        self.llm: Any = None

    def _get_llm(self) -> Any:
        """Lazy-init fallback-aware Bedrock client.

        Returns whatever was assigned to ``self.llm`` (test doubles), else
        builds a :class:`FallbackChatModel` for the configured task tier.
        """
        if self.llm is None:
            self.llm = build_chat_model(
                task_id=self.task_id,
                region=self.region,
                signals=ComplexitySignals(intent="ambiguous"),
                chat_cls=ChatBedrockConverse,
            )
        return self.llm

    async def run(
        self,
        messages: List[Dict[str, str]],
        tools: List[Any],
        system_prompt: str,
    ) -> str:
        """Run conversation loop.

        Args:
            messages: Conversation history
            tools: Available tools
            system_prompt: System prompt

        Returns:
            Assistant response
        """
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": system_prompt}, *messages]

        llm_client = self._get_llm()
        if tools:
            llm = llm_client.bind_tools(tools)
            response = await llm.ainvoke(messages)
        else:
            response = await llm_client.ainvoke(messages)
        return response.content

    async def run_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Any],
        system_prompt: str,
        on_delta: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Run conversation loop with streaming output.

        Args:
            messages: Conversation history
            tools: Available tools
            system_prompt: System prompt
            on_delta: Callback for each text delta

        Returns:
            Full assembled response text
        """
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": system_prompt}, *messages]

        llm_client = self._get_llm()
        parts: list[str] = []

        async for chunk in llm_client.astream(messages):
            content = chunk.content
            if isinstance(content, str):
                if content:
                    parts.append(content)
                    if on_delta:
                        on_delta(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        text = item["text"]
                        if text:
                            parts.append(text)
                            if on_delta:
                                on_delta(text)

        return "".join(parts)


__all__ = ["ConversationEngine", "FallbackChatModel"]
