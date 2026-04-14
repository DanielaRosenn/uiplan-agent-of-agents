"""Agentic executor with ReAct-style tool-use loop.

This module implements proper agentic skill execution where the LLM can
call tools iteratively until the task is complete.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


@dataclass
class AgenticResult:
    """Result from agentic skill execution."""
    
    success: bool
    final_response: str
    tool_calls_made: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    files_written: list[str] = field(default_factory=list)
    validation_status: str | None = None
    error: str | None = None


class AgenticExecutor:
    """Execute skills with ReAct-style tool-use loop.
    
    This implements the think-act-observe loop:
    1. LLM thinks about what to do and calls tools
    2. Tools execute and return results
    3. LLM observes results and decides next action
    4. Repeat until task complete or max iterations
    """
    
    MAX_ITERATIONS = 15
    
    def __init__(
        self,
        model_name: str,
        region: str,
        *,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str], None] | None = None,
    ):
        """Initialize the executor.
        
        Args:
            model_name: Bedrock model ID
            region: AWS region
            on_tool_call: Optional callback when a tool is called
            on_tool_result: Optional callback when a tool returns
        """
        self.model_name = model_name
        self.region = region
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self._llm: ChatBedrockConverse | None = None
    
    def _get_llm(self) -> ChatBedrockConverse:
        """Lazy-init Bedrock client."""
        if self._llm is None:
            self._llm = ChatBedrockConverse(
                model=self.model_name,
                region_name=self.region,
            )
        return self._llm
    
    async def execute(
        self,
        skill_content: str,
        user_request: str,
        tools: list,
        project_context: dict[str, Any] | None = None,
    ) -> AgenticResult:
        """Execute a skill with tool access.
        
        Args:
            skill_content: The skill's system prompt/instructions
            user_request: The user's request
            tools: List of LangChain tools available for use
            project_context: Optional context (output_dir, project_path, etc.)
        
        Returns:
            AgenticResult with final response and execution details
        """
        context = project_context or {}
        debug = os.environ.get("UIPATH_DEBUG_AGENT", "0").lower() in ("1", "true", "yes")
        
        # Build system prompt
        system_prompt = self._build_system_prompt(skill_content, context)
        
        # Initialize messages
        messages: list[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_request),
        ]
        
        # Get LLM with tools bound
        llm = self._get_llm()
        llm_with_tools = llm.bind_tools(tools)
        
        # Create tool lookup
        tool_map = {t.name: t for t in tools}
        
        tool_calls_made: list[dict[str, Any]] = []
        files_written: list[str] = []
        iterations = 0
        
        while iterations < self.MAX_ITERATIONS:
            iterations += 1
            
            if debug:
                print(f"[DEBUG] Iteration {iterations}/{self.MAX_ITERATIONS}")
            
            # Call LLM
            try:
                response = await llm_with_tools.ainvoke(messages)
            except Exception as e:
                return AgenticResult(
                    success=False,
                    final_response="",
                    tool_calls_made=tool_calls_made,
                    iterations=iterations,
                    files_written=files_written,
                    error=f"LLM call failed: {e}",
                )
            
            # Check for tool calls
            tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []
            
            if not tool_calls:
                # No tool calls - LLM is done
                final_text = response.content if isinstance(response.content, str) else str(response.content)
                return AgenticResult(
                    success=True,
                    final_response=final_text,
                    tool_calls_made=tool_calls_made,
                    iterations=iterations,
                    files_written=files_written,
                )
            
            # Process tool calls
            messages.append(response)  # Add AI message with tool calls
            
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")
                
                if debug:
                    print(f"[DEBUG] Tool call: {tool_name}({json.dumps(tool_args)[:200]})")
                
                if self.on_tool_call:
                    self.on_tool_call(tool_name, tool_args)
                
                tool_calls_made.append({
                    "name": tool_name,
                    "args": tool_args,
                    "iteration": iterations,
                })
                
                # Execute tool
                tool = tool_map.get(tool_name)
                if tool is None:
                    result = f"Error: Unknown tool '{tool_name}'"
                else:
                    try:
                        result = tool.invoke(tool_args)
                        if not isinstance(result, str):
                            result = str(result)
                    except Exception as e:
                        result = f"Error executing {tool_name}: {e}"
                
                # Track file writes
                if tool_name == "write_file" and "Successfully wrote" in result:
                    file_path = tool_args.get("file_path", "")
                    if file_path:
                        files_written.append(file_path)
                
                if debug:
                    print(f"[DEBUG] Tool result: {result[:300]}...")
                
                if self.on_tool_result:
                    self.on_tool_result(tool_name, result)
                
                # Add tool result message
                messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_id,
                    name=tool_name,
                ))
        
        # Max iterations reached
        return AgenticResult(
            success=False,
            final_response="",
            tool_calls_made=tool_calls_made,
            iterations=iterations,
            files_written=files_written,
            error=f"Max iterations ({self.MAX_ITERATIONS}) reached without completion",
        )
    
    def _build_system_prompt(
        self,
        skill_content: str,
        context: dict[str, Any],
    ) -> str:
        """Build the system prompt for skill execution."""
        parts = [
            "You are an expert UiPath automation developer executing a skill.",
            "",
            "## EXECUTION RULES",
            "",
            "1. You have access to tools for reading/writing files, running CLI commands, and validation.",
            "2. ALWAYS use tools to perform actions - do not just describe what you would do.",
            "3. After writing any XAML or .cs file, ALWAYS validate it with validate_file.",
            "4. If validation fails, fix the errors one at a time and re-validate.",
            "5. Check project.json dependencies before using activities - install missing packages.",
            "6. When done, provide a summary of what was created/modified.",
            "",
            "## PROJECT CONTEXT",
            "",
        ]
        
        if context.get("output_dir"):
            parts.append(f"Output directory: {context['output_dir']}")
        if context.get("project_path"):
            parts.append(f"Project path: {context['project_path']}")
        if context.get("session_id"):
            parts.append(f"Session ID: {context['session_id']}")
        
        parts.extend([
            "",
            "## SKILL INSTRUCTIONS",
            "",
            "Follow these instructions carefully:",
            "",
            skill_content,
        ])
        
        return "\n".join(parts)


async def run_agentic_skill(
    skill_content: str,
    user_request: str,
    tools: list,
    model_name: str,
    region: str,
    project_context: dict[str, Any] | None = None,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_tool_result: Callable[[str, str], None] | None = None,
) -> AgenticResult:
    """Convenience function to run a skill agentically.
    
    Args:
        skill_content: The skill's system prompt/instructions
        user_request: The user's request
        tools: List of LangChain tools available for use
        model_name: Bedrock model ID
        region: AWS region
        project_context: Optional context (output_dir, project_path, etc.)
        on_tool_call: Optional callback when a tool is called
        on_tool_result: Optional callback when a tool returns
    
    Returns:
        AgenticResult with final response and execution details
    """
    executor = AgenticExecutor(
        model_name=model_name,
        region=region,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
    )
    return await executor.execute(
        skill_content=skill_content,
        user_request=user_request,
        tools=tools,
        project_context=project_context,
    )
