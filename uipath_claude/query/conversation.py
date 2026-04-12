"""Conversation engine for agent interactions."""
from typing import List, Dict, Any
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
