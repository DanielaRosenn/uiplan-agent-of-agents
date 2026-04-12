"""Conversation engine for agent interactions."""
from typing import List, Dict, Any, Callable
from langchain_aws import ChatBedrockConverse


class ConversationEngine:
    """Conversation engine for model-tool-model loops."""
    
    def __init__(self, model_name: str, region: str):
        """
        Initialize conversation engine.
        
        Args:
            model_name: Bedrock model ID
            region: AWS region
        """
        self.model_name = model_name
        self.region = region
        self.llm = ChatBedrockConverse(
            model=model_name,
            region_name=region,
        )
    
    async def run(
        self,
        messages: List[Dict[str, str]],
        tools: List[Any],
        system_prompt: str,
    ) -> str:
        """
        Run conversation loop.
        
        Args:
            messages: Conversation history
            tools: Available tools
            system_prompt: System prompt
            
        Returns:
            Assistant response
        """
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": system_prompt}, *messages]

        if tools:
            llm = self.llm.bind_tools(tools)
            response = await llm.ainvoke(messages)
        else:
            response = await self.llm.ainvoke(messages)
        return response.content

    async def run_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Any],
        system_prompt: str,
        *,
        on_delta: Callable[[str], None] | None = None,
    ) -> str:
        """
        Stream model response while returning the full assembled text.

        Args:
            messages: Conversation history
            tools: Available tools
            system_prompt: System prompt
            on_delta: Optional callback called per text delta

        Returns:
            Full assistant response text
        """
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": system_prompt}, *messages]

        llm = self.llm.bind_tools(tools) if tools else self.llm
        parts: list[str] = []
        async for chunk in llm.astream(messages):
            delta = _extract_chunk_text(chunk)
            if not delta:
                continue
            parts.append(delta)
            if on_delta is not None:
                on_delta(delta)
        return "".join(parts)


def _extract_chunk_text(chunk: Any) -> str:
    """Best-effort extraction of text from a stream chunk."""
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: list[str] = []
        for part in content:
            if isinstance(part, str):
                out.append(part)
                continue
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    out.append(text)
                continue
            text = getattr(part, "text", None)
            if isinstance(text, str):
                out.append(text)
        return "".join(out)
    return ""
