"""Agentic executor with ReAct-style tool-use loop.

This module implements proper agentic skill execution where the LLM can
call tools iteratively until the task is complete.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from botocore.exceptions import ClientError
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from uipath_claude.observability.logger import StructuredLogger
from uipath_claude.query.plan_block import PLAN_BLOCK_HEADING, contains_plan_block
from uipath_claude.rendering.progress import AgenticProgressReporter
from uipath_claude.skills.execution_hook import post_skill_execution_hook
from uipath_claude.tools.approval import ApprovalPolicy

# Bedrock Converse toolUse.name must match provider constraints (alnum, underscore, hyphen; max 64).
_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MAX_BEDROCK_VALIDATION_RECOVERIES = 2


def _normalize_tool_name_for_bedrock(raw: str | None) -> tuple[str, bool]:
    """Return ``(name, was_rewritten)`` so ``name`` always matches ``_TOOL_NAME_RE`` when possible."""
    if raw is None or not str(raw).strip():
        return "invalid_tool", True
    name = str(raw).strip()
    m = re.match(r"^[A-Za-z0-9_-]+", name)
    base_full = m.group(0) if m else ""
    base = base_full[:64]
    if not base:
        return "invalid_tool", True
    if not _TOOL_NAME_RE.fullmatch(base):
        return "invalid_tool", True
    if base == name:
        return base, False
    return base, True


def _normalize_tool_calls_on_ai_response(response: Any) -> None:
    """Rewrite malformed tool names on the model message before appending to history."""
    tcs = getattr(response, "tool_calls", None)
    if not tcs:
        return
    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        orig = tc.get("name")
        norm, _ = _normalize_tool_name_for_bedrock(orig if isinstance(orig, str) else str(orig))
        tc["name"] = norm


def _strip_last_ai_tool_calls(messages: list[Any]) -> None:
    """Remove tool_calls from the most recent AIMessage (used after Bedrock ValidationException)."""
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            content = msg.content if isinstance(msg.content, str) else str(msg.content or "")
            messages[idx] = AIMessage(content=content, id=getattr(msg, "id", None))
            return


WRITE_TOOL_NAMES = frozenset(
    {
        "write_file",
        "ensure_project_structure",
        "deploy_to_orchestrator",
        "validate_file",
        "validate_and_fix_loop",
        "run_workflow",
        "debug_workflow",
    }
)


def _has_executed_plan(tool_calls_made: list[dict[str, Any]]) -> bool:
    return any(tc.get("name") in WRITE_TOOL_NAMES for tc in tool_calls_made)


def _tool_return_indicates_success(result: str) -> bool:
    """Prefer ``[OK]/[ERROR]`` markers; fall back to legacy substring rules for older tools."""
    if not isinstance(result, str):
        return False
    if result.startswith("[OK]"):
        return True
    if result.startswith("[ERROR]"):
        return False
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
    if re.search(r"\b0\s+errors?\b", rl) or "no errors" in rl:
        return True
    if "error" in rl:
        return False
    return True


def _is_tool_failure(observation: str) -> bool:
    """True if the tool observation should be treated as a failed tool call."""
    return not _tool_return_indicates_success(observation)


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
    tokens_in: int = 0
    tokens_out: int = 0


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

    def _approve_lesson(self, candidate: Any) -> bool:
        if os.environ.get("UIPATH_LESSON_AUTO_APPROVE", "0").strip() == "1":
            return True
        prompter = getattr(self, "lesson_prompter", None)
        if prompter is None:
            return False
        return bool(prompter(candidate))

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
        if result.success:
            return
        try:
            from uipath_claude.skills.insights import InsightLayer, SkillInsightsStore
            from uipath_claude.skills.lessons import propose_from_failure

            failing_tool = None
            for tc in reversed(result.tool_calls_made):
                if tc.get("ok") is False:
                    failing_tool = tc.get("name")
                    break
            if failing_tool is None and result.tool_calls_made:
                failing_tool = result.tool_calls_made[-1].get("name")

            candidate = propose_from_failure(
                skill_name=skill_name,
                user_request=user_request,
                failing_tool=failing_tool,
                error_message=result.error,
            )
            if not self._approve_lesson(candidate):
                return
            project_root = Path(os.environ.get("UIPATH_PROJECT_ROOT") or Path.cwd())
            SkillInsightsStore(project_root=project_root).append(
                candidate, layer=InsightLayer.PROJECT
            )
        except Exception:
            pass

    def __init__(
        self,
        model_name: str,
        region: str,
        *,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str], None] | None = None,
        approval: ApprovalPolicy | None = None,
        lesson_prompter: Callable[[Any], bool] | None = None,
    ):
        """Initialize the executor.
        
        Args:
            model_name: Bedrock model ID
            region: AWS region
            on_tool_call: Optional callback when a tool is called
            on_tool_result: Optional callback when a tool returns
            approval: Optional policy gate for destructive tools
            lesson_prompter: Optional callback to approve proposed lessons (CLI)
        """
        self.model_name = model_name
        self.region = region
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.approval = approval
        self.lesson_prompter = lesson_prompter
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

        skill_body = skill_content
        try:
            from uipath_claude.skills.lessons import load_for_skill, render_lessons_block

            project_root = Path(os.environ.get("UIPATH_PROJECT_ROOT") or Path.cwd())
            ranked = load_for_skill(skill_name, project_root=project_root)
            lessons_block = render_lessons_block(ranked, project_root=project_root)
            if lessons_block:
                skill_body = f"{skill_content}\n\n{lessons_block}"
        except Exception:
            skill_body = skill_content

        system_prompt = self._build_system_prompt(skill_body, context)

        messages: list[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_request),
        ]

        llm = self._get_llm()
        llm_with_tools = llm.bind_tools(tools)

        tool_map = {t.name: t for t in tools}

        tool_calls_made: list[dict[str, Any]] = []
        files_written: list[str] = []
        iterations = 0
        tool_success_count = 0
        tool_failure_count = 0
        plan_tool_nudges = 0
        tokens_in_total = 0
        tokens_out_total = 0
        struct_log = StructuredLogger()
        session_log_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        validation_recovery_attempts = 0

        while iterations < max_iter:
            iterations += 1

            struct_log.emit(
                event="iteration_start",
                session_id=session_log_id,
                skill=skill_name,
                iteration=iterations,
                tool=None,
                ok=None,
            )

            if progress:
                progress.iteration_start(iterations, max_iter)
                progress.thinking()

            try:
                response = await llm_with_tools.ainvoke(messages)
            except ClientError as e:
                err = (getattr(e, "response", None) or {}).get("Error", {}) or {}
                if (
                    err.get("Code") == "ValidationException"
                    and validation_recovery_attempts < _MAX_BEDROCK_VALIDATION_RECOVERIES
                ):
                    validation_recovery_attempts += 1
                    struct_log.emit(
                        event="bedrock_validation_recovery",
                        session_id=session_log_id,
                        skill=skill_name,
                        iteration=iterations,
                        tool=None,
                        ok=False,
                        extra={"attempt": validation_recovery_attempts},
                    )
                    if progress:
                        progress.info(
                            "Bedrock ValidationException; stripping bad tool calls and retrying "
                            f"({validation_recovery_attempts}/{_MAX_BEDROCK_VALIDATION_RECOVERIES})."
                        )
                    _strip_last_ai_tool_calls(messages)
                    messages.append(
                        HumanMessage(
                            content=(
                                "SYSTEM: The provider rejected the previous request (invalid "
                                "tool_use). Re-issue tool calls using only registered tool names "
                                "(letters, digits, underscore, hyphen) and JSON arguments only — "
                                "no XML fragments or quotes inside the tool name."
                            )
                        )
                    )
                    continue
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
                    tokens_in=tokens_in_total,
                    tokens_out=tokens_out_total,
                )
                self._record_learning(skill_name, user_request, err_result)
                return err_result
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
                    tokens_in=tokens_in_total,
                    tokens_out=tokens_out_total,
                )
                self._record_learning(skill_name, user_request, err_result)
                return err_result

            _normalize_tool_calls_on_ai_response(response)

            usage = getattr(response, "usage_metadata", None) or {}
            tokens_in_total += int(usage.get("input_tokens") or 0)
            tokens_out_total += int(usage.get("output_tokens") or 0)

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

                # Approved plan was merged into skill_content (see cli chat + execute node) but the
                # model sometimes replies with prose only (possibly after read-only tools). Nudge
                # until a write/validation/deploy tool runs.
                if (
                    contains_plan_block(skill_content)
                    and not _has_executed_plan(tool_calls_made)
                    and plan_tool_nudges < 5
                    and iterations < max_iter
                ):
                    plan_tool_nudges += 1
                    messages.append(response)
                    nudge = (
                        f"SYSTEM: Your skill instructions include `{PLAN_BLOCK_HEADING}`. "
                        "You must not finish with text only — call tools now and execute that plan "
                        "(e.g. read_project_json, list_directory, ensure_project_structure, write_file). "
                        "Start with discovery or scaffolding, then implement. Plain summaries alone are invalid."
                    )
                    messages.append(HumanMessage(content=nudge))
                    if progress:
                        progress.info(
                            "Approved plan present but no write/validation/deploy-class tool yet; "
                            f"requesting tool calls ({plan_tool_nudges}/5)."
                        )
                    continue

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
                        tokens_in=tokens_in_total,
                        tokens_out=tokens_out_total,
                    )
                struct_log.emit(
                    event="complete",
                    session_id=session_log_id,
                    skill=skill_name,
                    iteration=iterations,
                    tool=None,
                    ok=True,
                    tokens_in=tokens_in_total,
                    tokens_out=tokens_out_total,
                    files_written=files_written,
                )
                ok_result = AgenticResult(
                    success=True,
                    final_response=final_text,
                    tool_calls_made=tool_calls_made,
                    iterations=iterations,
                    files_written=files_written,
                    tool_success_count=tool_success_count,
                    tool_failure_count=tool_failure_count,
                    tokens_in=tokens_in_total,
                    tokens_out=tokens_out_total,
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

                t0 = time.monotonic()
                tool = tool_map.get(tool_name)
                if self.approval is not None and not self.approval.check(tool_name, tool_args):
                    result = "[ERROR] Tool call blocked by approval policy."
                    success = False
                elif tool is None:
                    result = f"[ERROR] Unknown tool '{tool_name}'"
                    success = False
                else:
                    try:
                        result = tool.invoke(tool_args)
                        if not isinstance(result, str):
                            result = str(result)
                        success = not _is_tool_failure(result)
                    except Exception as e:
                        result = f"[ERROR] Error executing {tool_name}: {e}"
                        success = False

                elapsed_ms = int((time.monotonic() - t0) * 1000)
                struct_log.emit(
                    event="tool_call",
                    session_id=session_log_id,
                    skill=skill_name,
                    iteration=iterations,
                    tool=tool_name,
                    ok=success,
                    ms=elapsed_ms,
                )

                tool_calls_made.append(
                    {
                        "name": tool_name,
                        "args": tool_args,
                        "iteration": iterations,
                        "ok": success,
                    }
                )

                if success:
                    tool_success_count += 1
                else:
                    tool_failure_count += 1

                if tool_name == "write_file" and (
                    "Successfully wrote" in result
                    or ("[OK]" in result and "wrote" in result.lower())
                ):
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

                messages.append(
                    ToolMessage(
                        content=result,
                        tool_call_id=tool_id,
                        name=tool_name,
                    )
                )
        
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
            tokens_in=tokens_in_total,
            tokens_out=tokens_out_total,
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
            f'2b. If SKILL INSTRUCTIONS contain "{PLAN_BLOCK_HEADING}", that block is your '
            "ordered checklist: implement it with tools (scaffold, read/write files, validate) before you stop.",
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
