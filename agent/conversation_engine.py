# agent/conversation_engine.py
"""Conversation engine with model-tools-model loop."""

from typing import List, Optional
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import BaseTool

MAX_TOOL_ITERATIONS = 10


class ConversationEngine:
    """
    Manages the model-tools-model conversation loop.

    Similar to Claude Code's query.ts + toolOrchestration.ts pattern.
    The engine invokes the model, executes any tool calls, feeds results
    back to the model, and repeats until the model responds without
    tool calls or MAX_TOOL_ITERATIONS is reached.
    """

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region: str = "us-east-1",
        temperature: float = 0.3,
        tools: Optional[List[BaseTool]] = None,
    ):
        self.model_id = model_id
        self.region = region
        self.temperature = temperature
        self.tools = tools or []
        self._llm = None

    @property
    def llm(self) -> ChatBedrockConverse:
        """Lazy-initialize LLM with tools bound."""
        if self._llm is None:
            self._llm = ChatBedrockConverse(
                model=self.model_id,
                region_name=self.region,
                temperature=self.temperature,
            )
            if self.tools:
                self._llm = self._llm.bind_tools(self.tools)
        return self._llm

    async def run_turn(
        self,
        messages: List[BaseMessage],
        system_prompt: Optional[str] = None,
    ) -> AIMessage:
        """
        Run a complete conversation turn with tool loop.

        Args:
            messages: Conversation history
            system_prompt: Optional system prompt to prepend

        Returns:
            Final AIMessage after tool loop completes
        """
        all_messages = []
        if system_prompt:
            all_messages.append(SystemMessage(content=system_prompt))
        all_messages.extend(messages)

        iterations = 0

        while iterations <= MAX_TOOL_ITERATIONS:
            response = await self._invoke_model(all_messages)
            all_messages.append(response)

            if not response.tool_calls:
                return response

            tool_results = await self._execute_tools(response.tool_calls)
            all_messages.extend(tool_results)
            iterations += 1

        return AIMessage(content="[Max tool iterations reached. Please try a simpler request.]")

    async def _invoke_model(self, messages: List[BaseMessage]) -> AIMessage:
        """Invoke the LLM with messages."""
        return await self.llm.ainvoke(messages)

    async def _execute_tools(self, tool_calls: List[dict]) -> List[ToolMessage]:
        """Execute tool calls and return results."""
        results = []

        for call in tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})
            tool_id = call.get("id")

            tool = self._find_tool(tool_name)
            if tool:
                try:
                    result = await tool.ainvoke(tool_args)
                    results.append(ToolMessage(content=str(result), tool_call_id=tool_id))
                except Exception as e:
                    results.append(
                        ToolMessage(
                            content=f"Error: {type(e).__name__}: {str(e)}",
                            tool_call_id=tool_id,
                        )
                    )
            else:
                results.append(
                    ToolMessage(
                        content=f"Error: Tool '{tool_name}' not found",
                        tool_call_id=tool_id,
                    )
                )

        return results

    def _find_tool(self, name: str) -> Optional[BaseTool]:
        """Find a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
