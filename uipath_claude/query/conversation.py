"""Conversation engine for agent interactions."""
from typing import List, Dict, Any, Callable, Optional
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
        self.llm = None

    def _get_llm(self) -> ChatBedrockConverse:
        """Lazy-init Bedrock client so construction does not require credentials."""
        if self.llm is None:
            self.llm = ChatBedrockConverse(
                model=self.model_name,
                region_name=self.region,
            )
        return self.llm
    
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
        """
        Run conversation loop with streaming output.
        
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
