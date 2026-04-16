"""Agentic executor with ReAct-style tool-use loop.

This module implements proper agentic skill execution where the LLM can
call tools iteratively until the task is complete.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from uipath_claude.rendering.progress import AgenticProgressReporter
from uipath_claude.skills.execution_hook import post_skill_execution_hook


def _tool_return_indicates_success(result: str) -> bool:
    """Infer success from tool return text (best-effort; avoids false negatives)."""
    rl = result.lower().strip()
    if "failed" in rl:
        return False
    if rl.startswith("error:"):
        return False
    if "error executing" in rl:
        return False
    if "unknown tool" in rl:
        return False
    if "workflow file not found" in rl or "file not found" in rl:
        return False
    # "0 errors", "no errors" contain substring "error" — treat as success
    if re.search(r"\b0\s+errors?\b", rl) or "no errors" in rl:
        return True
    if "error" in rl:
        return False
    return True


@dataclass
class AgenticResult:
    """Result from agentic skill execution.

    ``success`` means the LLM finished the loop (no tool calls) or similar
    normal completion—not that every tool returned without error. Use
    ``tool_failure_count`` for per-tool outcomes.
    """

    success: bool
    final_response: str
    tool_calls_made: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    files_written: list[str] = field(default_factory=list)
    validation_status: str | None = None
    error: str | None = None
    tool_success_count: int = 0
    tool_failure_count: int = 0


class AgenticExecutor:
    """Execute skills with ReAct-style tool-use loop.
    
    This implements the think-act-observe loop:
    1. LLM thinks about what to do and calls tools
    2. Tools execute and return results
    3. LLM observes results and decides next action
    4. Repeat until task complete or max iterations
    """
    
    MAX_ITERATIONS = int(os.environ.get("UIPATH_MAX_ITERATIONS", "25"))

    @staticmethod
    def _learning_capture_enabled() -> bool:
        return os.environ.get("UIPATH_SKILL_AUTO_CAPTURE", "1").lower() in (
            "1",
            "true",
            "yes",
        )

    def _record_learning(
        self,
        skill_name: str,
        user_request: str,
        result: AgenticResult,
    ) -> None:
        if not self._learning_capture_enabled():
            return
        post_skill_execution_hook(
            skill_name=skill_name,
            success=result.success,
            tool_calls=len(result.tool_calls_made),
            error=result.error,
            context=user_request[:500],
        )

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
        *,
        skill_name: str = "unknown",
        max_iterations: int | None = None,
    ) -> AgenticResult:
        """Execute a skill with tool access.
        
        Args:
            skill_content: The skill's system prompt/instructions
            user_request: The user's request
            tools: List of LangChain tools available for use
            project_context: Optional context (output_dir, project_path, etc.)
            skill_name: Primary skill name for learning/telemetry attribution
            max_iterations: Cap ReAct iterations (default: class ``MAX_ITERATIONS``).
        
        Returns:
            AgenticResult with final response and execution details
        """
        context = project_context or {}
        max_iter = self.MAX_ITERATIONS if max_iterations is None else max_iterations
        if max_iter < 1:
            max_iter = 1
        debug = os.environ.get("UIPATH_DEBUG_AGENT", "1").lower() in ("1", "true", "yes")
        
        # Initialize progress reporter if debug enabled (on by default)
        progress = AgenticProgressReporter() if debug else None

        out_dir = (context.get("output_dir") or "").strip()
        sess_id = (context.get("session_id") or "").strip()
        artifact_root: str | None = None
        if out_dir and sess_id:
            artifact_root = str((Path(out_dir).expanduser().resolve() / sess_id))
        if progress:
            progress.session_banner(artifact_root)
            raw_skills = context.get("selected_skill_names")
            if isinstance(raw_skills, list) and raw_skills:
                progress.skills_in_context(
                    [str(s) for s in raw_skills],
                    skill_name,
                )

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
        tool_success_count = 0
        tool_failure_count = 0

        while iterations < max_iter:
            iterations += 1
            
            if progress:
                progress.iteration_start(iterations, max_iter)
                progress.thinking()
            
            # Call LLM
            try:
                response = await llm_with_tools.ainvoke(messages)
            except Exception as e:
                if progress:
                    progress.error(str(e))
                err_result = AgenticResult(
                    success=False,
                    final_response="",
                    tool_calls_made=tool_calls_made,
                    iterations=iterations,
                    files_written=files_written,
                    error=f"LLM call failed: {e}",
                    tool_success_count=tool_success_count,
                    tool_failure_count=tool_failure_count,
                )
                self._record_learning(skill_name, user_request, err_result)
                return err_result
            
            # Check for tool calls
            tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []
            
            if not tool_calls:
                # No tool calls - LLM is done
                final_text = response.content if isinstance(response.content, str) else str(response.content)
                
                # Check if there are validation errors in recent tool results
                has_validation_errors = self._check_for_validation_errors(messages)
                
                if has_validation_errors and iterations < max_iter:
                    # Force continuation to fix validation errors
                    if progress:
                        progress.error("Validation errors detected - requesting fixes...")
                    
                    fix_instruction = (
                        "CRITICAL: The workflow has validation errors that must be fixed. "
                        "Review the validation error messages above, fix the errors one at a time, "
                        "and call validate_file again until there are 0 errors. "
                        "Do NOT stop until validation passes completely."
                    )
                    messages.append(HumanMessage(content=fix_instruction))
                    continue  # Continue the loop to fix validation errors
                
                if progress:
                    progress.model_finished_without_tools(
                        iteration=iterations,
                        had_tool_calls_before=bool(tool_calls_made),
                        final_text=final_text,
                    )
                    progress.complete(
                        files_written,
                        iterations,
                        tool_success_count=tool_success_count,
                        tool_failure_count=tool_failure_count,
                        artifact_root=artifact_root,
                    )
                ok_result = AgenticResult(
                    success=True,
                    final_response=final_text,
                    tool_calls_made=tool_calls_made,
                    iterations=iterations,
                    files_written=files_written,
                    tool_success_count=tool_success_count,
                    tool_failure_count=tool_failure_count,
                )
                self._record_learning(skill_name, user_request, ok_result)
                return ok_result
            
            # Process tool calls
            messages.append(response)  # Add AI message with tool calls
            
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")
                
                if progress:
                    progress.tool_call(tool_name, tool_args)
                
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
                    success = False
                else:
                    try:
                        result = tool.invoke(tool_args)
                        if not isinstance(result, str):
                            result = str(result)
                        success = _tool_return_indicates_success(result)
                    except Exception as e:
                        result = f"Error executing {tool_name}: {e}"
                        success = False

                if success:
                    tool_success_count += 1
                else:
                    tool_failure_count += 1

                # Track file writes
                if tool_name == "write_file" and "Successfully wrote" in result:
                    file_path = tool_args.get("file_path", "")
                    if file_path:
                        files_written.append(file_path)
                
                if progress:
                    progress.tool_result(
                        tool_name,
                        success,
                        result,
                        show_full_body=progress.should_show_full_tool_body(success),
                    )
                
                if self.on_tool_result:
                    self.on_tool_result(tool_name, result)
                
                # Add tool result message
                messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_id,
                    name=tool_name,
                ))
        
        # Max iterations reached
        if progress:
            progress.error(f"Max iterations ({max_iter}) reached without completion")
        max_iter_result = AgenticResult(
            success=False,
            final_response="",
            tool_calls_made=tool_calls_made,
            iterations=iterations,
            files_written=files_written,
            error=f"Max iterations ({max_iter}) reached without completion",
            tool_success_count=tool_success_count,
            tool_failure_count=tool_failure_count,
        )
        self._record_learning(skill_name, user_request, max_iter_result)
        return max_iter_result
    
    def _check_for_validation_errors(self, messages: list[Any]) -> bool:
        """Check if recent tool results contain validation errors.
        
        Args:
            messages: Message history
            
        Returns:
            True if validation errors found, False otherwise
        """
        # Look at last 5 messages for validation errors
        recent_messages = messages[-5:] if len(messages) >= 5 else messages
        
        for msg in recent_messages:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                content_lower = msg.content.lower()
                # Check for validation failure indicators
                if ("validation failed" in content_lower or 
                    "validation error" in content_lower or
                    "error(s)" in content_lower) and "validate" in content_lower:
                    # Make sure it's not "0 errors"
                    if "0 error" not in content_lower and "passed" not in content_lower:
                        return True
        
        return False
    
    def _build_system_prompt(
        self,
        skill_content: str,
        context: dict[str, Any],
    ) -> str:
        """Build the system prompt for skill execution."""
        parts = [
            "You are UiPath Claude Code, an expert agentic AI assistant executing a skill.",
            "You have direct access to the user's local file system, UiPath CLI, and UiPath skills.",
            "NEVER say you don't have access to tools, skills, or the local environment.",
            "",
            "## EXECUTION RULES",
            "",
            "1. You have access to tools for reading/writing files, running CLI commands, validation, and deployment.",
            "2. ALWAYS use tools to perform actions - do not just describe what you would do.",
            "3. After writing any XAML or .cs file, ALWAYS validate it with validate_file.",
            "4. If validation fails, fix the errors one at a time and re-validate.",
            "5. CRITICAL: Do NOT stop or finish until validation passes (0 errors). Keep fixing and re-validating.",
            "6. Check project.json dependencies before using activities - install missing packages.",
            "7. If user requests deployment/publishing, use deploy_to_orchestrator after validation passes.",
            "8. When done AND validation passes, provide a summary of what was created/modified.",
            "9. For write_file and other session-scoped paths, use paths relative to the chat "
            "artifact root only — do not pass Windows absolute paths to write_file.",
            "10. Do not pass --use-studio to the uip CLI via run_uip_command; it is not "
            "supported on all CLI versions.",
            "",
            "## DEPLOYMENT",
            "You can deploy workflows to Orchestrator or Studio Web using deploy_to_orchestrator.",
            "Deploy when user says: 'deploy', 'publish', 'upload to orchestrator', 'deploy to studio web'.",
            "Requires: UIPATH_ORCHESTRATOR_URL and UIPATH_TENANT_NAME (from environment or parameters).",
            "Default folder: Test (user can specify Dev, Prod, Test, or custom folder).",
            "If deployment fails with missing config, guide user to set environment variables.",
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
    *,
    skill_name: str = "unknown",
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
        skill_name: Primary skill for learning attribution (passed through to ``execute``).

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
        skill_name=skill_name,
    )
