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
from typing import Any, Callable, Mapping

from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from uipath_claude.llm.invoke import FallbackChatModel, build_chat_model
from uipath_claude.llm.routing.complexity import ComplexitySignals
from uipath_claude.observability.logger import StructuredLogger
from uipath_claude.query.plan_block import PLAN_BLOCK_HEADING, contains_plan_block
from uipath_claude.rendering.progress import AgenticProgressReporter
from uipath_claude.skills.execution_hook import post_skill_execution_hook
from uipath_claude.tools.approval import ApprovalPolicy

# Bedrock Converse toolUse.name must match provider constraints (alnum, underscore, hyphen; max 64).
_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MAX_BEDROCK_VALIDATION_RECOVERIES = 2
_MAX_BEDROCK_TIMEOUT_RECOVERIES = 2


def _bedrock_read_timeout_seconds() -> int:
    raw = (os.environ.get("UIPATH_BEDROCK_READ_TIMEOUT") or "").strip()
    try:
        value = int(raw) if raw else 300
    except ValueError:
        value = 300
    return max(30, value)


def _bedrock_connect_timeout_seconds() -> int:
    raw = (os.environ.get("UIPATH_BEDROCK_CONNECT_TIMEOUT") or "").strip()
    try:
        value = int(raw) if raw else 10
    except ValueError:
        value = 10
    return max(1, value)


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
        "uipath_workflow_write_file",
        "ensure_project_structure",
        "deploy_to_orchestrator",
        "uipath_workflow_deploy",
        "validate_file",
        "validate_and_fix_loop",
        "build_and_verify_workflow",
        "uipath_workflow_build_and_verify",
        "create_project",
        "uipath_workflow_create_project",
        "run_workflow",
        "debug_workflow",
        "create_xaml_workflow",
        "uipath_workflow_create_xaml_workflow",
        "validate_xaml",
        "install_package",
        "uipath_workflow_install_package",
    }
)


def _has_executed_plan(tool_calls_made: list[dict[str, Any]]) -> bool:
    return any(tc.get("name") in WRITE_TOOL_NAMES for tc in tool_calls_made)


_BUILD_VERIFY_NAMES = frozenset(
    {"build_and_verify_workflow", "uipath_workflow_build_and_verify"}
)
_DESIGN_PROPOSE_NAMES = frozenset({"uipath_design_propose"})
_PROJECT_MUTATING_NAMES = frozenset(
    {
        "write_file",
        "uipath_workflow_write_file",
        "install_package",
        "uipath_workflow_install_package",
        "deploy_to_orchestrator",
        "uipath_workflow_deploy",
        "ensure_project_structure",
        "create_project",
        "uipath_workflow_create_project",
        "create_xaml_workflow",
        "uipath_workflow_create_xaml_workflow",
    }
)


def _last_build_verify_was_pass(messages: list[Any]) -> tuple[bool, str | None]:
    """Inspect the most recent build_and_verify result.

    Returns ``(passed, reason)`` where ``passed`` is True iff the most recent
    build_and_verify ToolMessage carried ``verdict='pass'`` (or
    ``success=true`` for legacy formats). When no build_and_verify call has
    been made, ``passed=False`` and ``reason`` explains.
    """
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        name = getattr(msg, "name", "") or ""
        if name not in _BUILD_VERIFY_NAMES:
            continue
        content = msg.content if isinstance(msg.content, str) else str(msg.content or "")
        cl = content.lower()
        if "verdict='pass'" in cl or '"verdict": "pass"' in cl or "verdict=pass" in cl:
            return True, None
        if "verdict='needs_human'" in cl or '"verdict": "needs_human"' in cl:
            return False, "build_and_verify returned verdict='needs_human'"
        if "verdict='needs_llm_fix'" in cl or '"verdict": "needs_llm_fix"' in cl:
            return False, "build_and_verify returned verdict='needs_llm_fix'"
        if content.startswith("[OK]") and ("verdict" not in cl):
            return True, None
        return False, "build_and_verify did not report verdict='pass'"
    return False, "build_and_verify_workflow has not been called yet"


def _has_mutated_project(tool_calls_made: list[dict[str, Any]]) -> bool:
    return any(tc.get("name") in _PROJECT_MUTATING_NAMES for tc in tool_calls_made)


def _build_verify_tool_available(tool_map: Mapping[str, Any]) -> bool:
    """True when the bound tool set includes a workflow build/verify tool."""
    return bool(_BUILD_VERIFY_NAMES & frozenset(tool_map.keys()))


# Tools that should be redirected to `uipath_design_propose` when the target
# project has no approved design. Subset of `_PROJECT_MUTATING_NAMES` — deploy
# and build_and_verify are excluded because the underlying MCP gates already
# return [BLOCKED] with actionable messaging for those.
_WRITE_INTENT_TOOL_NAMES = frozenset(
    {
        "write_file",
        "uipath_workflow_write_file",
        "install_package",
        "uipath_workflow_install_package",
        "ensure_project_structure",
        "create_project",
        "uipath_workflow_create_project",
        "create_xaml_workflow",
        "uipath_workflow_create_xaml_workflow",
    }
)


# Common LLM hallucinations for the design-propose / design-approve MCP tools.
# When the model invokes one of these, return a one-line redirect describing
# the real tool name (or, when the gate is disabled, tell the model to skip
# the propose/approve dance altogether) instead of the bare "Unknown tool".
_DESIGN_TOOL_ALIASES = {
    "uipath_workflow_design_propose": "uipath_design_propose",
    "uipath_rpa_design_propose": "uipath_design_propose",
    "uipath_project_design_propose": "uipath_design_propose",
    "design_propose": "uipath_design_propose",
    "propose_design": "uipath_design_propose",
    "uipath_workflow_design_approve": "uipath_design_approve",
    "uipath_rpa_design_approve": "uipath_design_approve",
    "uipath_project_design_approve": "uipath_design_approve",
    "design_approve": "uipath_design_approve",
    "approve_design": "uipath_design_approve",
}


def _design_alias_message(called_name: str, real_name: str) -> str:
    """Explain how to recover from a hallucinated design-tool name."""
    from uipath_claude.tools import design_store

    if not design_store._approval_enabled():
        return (
            f"[ERROR] Unknown tool '{called_name}'. The design gate is "
            "DISABLED for this session (UIPATH_DESIGN_APPROVAL_ENABLED=0). "
            "Do NOT call any design-propose/approve tool. Proceed directly "
            "to write_file / install_package / ensure_project_structure / "
            "build_and_verify with the correct project_dir."
        )
    return (
        f"[ERROR] Unknown tool '{called_name}'. The correct tool name is "
        f"'{real_name}'. Retry with the same arguments but call "
        f"'{real_name}' instead."
    )


def _resolve_project_dir_from_context(context: dict[str, Any]) -> str | None:
    """Resolve the target project_dir for the design-gate preflight.

    Order: ``project_context['project_path']`` > ``UIPATH_PROJECT_DIR`` env.
    Returns ``None`` when no candidate resolves to an existing directory.
    """
    candidates: list[str] = []
    pp = context.get("project_path") if context else None
    if isinstance(pp, str) and pp.strip():
        candidates.append(pp.strip())
    env_pd = os.environ.get("UIPATH_PROJECT_DIR", "").strip()
    if env_pd:
        candidates.append(env_pd)
    for c in candidates:
        try:
            p = Path(c).expanduser()
            if p.exists() and p.is_dir():
                return str(p.resolve())
        except Exception:
            continue
    return None


def _extract_project_dir_from_tool_args(tool_args: dict[str, Any]) -> str | None:
    """Pull a project_dir-ish path out of a tool call's arguments, if present."""
    for key in ("project_dir", "project_path", "projectDir", "projectPath"):
        val = tool_args.get(key) if isinstance(tool_args, dict) else None
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _redirect_to_design_propose(project_dir: str, tool_name: str) -> str:
    """Synthetic tool result shown when a write-intent tool hits a closed gate.

    Instructs the model to call `uipath_design_propose` instead of attempting
    the write. Keeps the loop going (the model can then propose + ask the user
    to approve) without silently no-op'ing the turn.
    """
    return (
        f"[REDIRECT] Project '{project_dir}' has no approved design. "
        f"Do NOT call {tool_name} yet. Stage one now:\n"
        "  uipath_design_propose { project_dir, title, summary, body, resolutions }\n"
        "Then ask the user to approve via uipath_design_approve on the "
        "returned design_id. Do NOT call write tools until approved."
    )


def _has_blocked_observation(messages: list[Any], lookback: int = 8) -> bool:
    """True when a recent ToolMessage contains a session/design gate block."""
    recent = messages[-lookback:] if len(messages) >= lookback else messages
    for msg in recent:
        if not isinstance(msg, ToolMessage):
            continue
        content = msg.content if isinstance(msg.content, str) else str(msg.content or "")
        if content.startswith("[BLOCKED]"):
            return True
    return False


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
        model_name: str | None = None,
        region: str | None = None,
        *,
        on_tool_call: Callable[[str, dict], None] | None = None,
        on_tool_result: Callable[[str, str], None] | None = None,
        approval: ApprovalPolicy | None = None,
        lesson_prompter: Callable[[Any], bool] | None = None,
    ):
        """Initialize the executor.

        Args:
            model_name: Optional Bedrock model ID override (legacy; routing
                helper normally resolves the model from the ``agentic_executor``
                task tier).
            region: AWS region (defaults to ``AWS_REGION`` env var).
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
        self._llm: FallbackChatModel | None = None

    def _get_llm(self) -> FallbackChatModel:
        """Lazy-init fallback-aware Bedrock client.

        Routes through :func:`uipath_claude.llm.invoke.build_chat_model` so
        ``invoke``/``ainvoke`` calls inside the LangChain agent loop fall
        back to the tier's fallback model on model-related failures.
        """
        if self._llm is None:
            boto_cfg = BotoConfig(
                read_timeout=_bedrock_read_timeout_seconds(),
                connect_timeout=_bedrock_connect_timeout_seconds(),
                retries={"max_attempts": 3, "mode": "adaptive"},
            )
            self._llm = build_chat_model(
                task_id="agentic_executor",
                region=self.region,
                signals=ComplexitySignals(intent="build", planner_triggered=True),
                extra_kwargs={"config": boto_cfg},
                chat_cls=ChatBedrockConverse,
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
        prior_messages: list[dict[str, str]] | None = None,
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

        preflight_project_dir = _resolve_project_dir_from_context(context)
        preflight_approved = False
        preflight_pending_id: str | None = None
        if preflight_project_dir:
            try:
                from uipath_claude.tools import design_store

                preflight_approved = design_store.has_approved(preflight_project_dir)
                pending = design_store.latest_pending(preflight_project_dir)
                preflight_pending_id = pending.design_id if pending else None
            except Exception:
                preflight_project_dir = None
        if progress and preflight_project_dir:
            progress.design_gate_banner(
                preflight_project_dir,
                preflight_approved,
                preflight_pending_id,
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

        messages: list[Any] = [SystemMessage(content=system_prompt)]
        if prior_messages:
            for msg in prior_messages:
                role = (msg.get("role") or "").lower()
                content = msg.get("content") or ""
                if not content:
                    continue
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=user_request))

        if preflight_project_dir:
            try:
                from uipath_claude.tools import design_store as _ds

                _gate_enabled = _ds._approval_enabled()
            except Exception:
                _gate_enabled = True
            if not _gate_enabled:
                gate_hint = (
                    f"[DESIGN_GATE] project={preflight_project_dir} disabled=true "
                    "-> UIPATH_DESIGN_APPROVAL_ENABLED is OFF for this session. "
                    "Do NOT call uipath_design_propose or uipath_design_approve. "
                    "Proceed directly with write_file / install_package / "
                    "ensure_project_structure / build_and_verify, passing "
                    f"project_dir='{preflight_project_dir}' on every call."
                )
            elif preflight_approved:
                gate_hint = (
                    f"[DESIGN_GATE] project={preflight_project_dir} approved=true "
                    "-> write_file / install_package / ensure_project_structure are "
                    "allowed for this project without a new design proposal."
                )
            elif preflight_pending_id:
                gate_hint = (
                    f"[DESIGN_GATE] project={preflight_project_dir} approved=false "
                    f"pending={preflight_pending_id} -> you MUST wait for "
                    "uipath_design_approve on this design_id before calling any "
                    "write/install/scaffold tools. Any such call will be "
                    "redirected back to uipath_design_propose."
                )
            else:
                gate_hint = (
                    f"[DESIGN_GATE] project={preflight_project_dir} approved=false "
                    "pending=none -> your FIRST tool call for any write/install/"
                    "scaffold step MUST be uipath_design_propose (with a short "
                    "user-facing summary, body, and resolutions). After the user "
                    "approves via uipath_design_approve, writes become allowed."
                )
            messages.append(SystemMessage(content=gate_hint))

        llm = self._get_llm()
        llm_with_tools = llm.bind_tools(tools)

        tool_map = {t.name: t for t in tools}

        tool_calls_made: list[dict[str, Any]] = []
        files_written: list[str] = []
        iterations = 0
        tool_success_count = 0
        tool_failure_count = 0
        design_blocked = False
        plan_tool_nudges = 0
        verify_nudges = 0
        tokens_in_total = 0
        tokens_out_total = 0
        struct_log = StructuredLogger()
        session_log_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        validation_recovery_attempts = 0
        timeout_recovery_attempts = 0
        consecutive_unknown_tool = 0

        # Dynamic iteration budget: extend once by +10 steps if the agent is
        # still making progress as the ceiling approaches. "Progress" =
        # at least 2 successful tool calls in the trailing 5-call window.
        # Controlled by ``UIPATH_MAX_ITER_EXTEND`` (default 10, set to 0 to
        # disable).
        try:
            _iter_extend = int(os.environ.get("UIPATH_MAX_ITER_EXTEND", "10"))
        except ValueError:
            _iter_extend = 10
        _budget_extended = False

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
            except (ReadTimeoutError, ConnectTimeoutError) as e:
                if timeout_recovery_attempts < _MAX_BEDROCK_TIMEOUT_RECOVERIES:
                    timeout_recovery_attempts += 1
                    struct_log.emit(
                        event="bedrock_timeout_recovery",
                        session_id=session_log_id,
                        skill=skill_name,
                        iteration=iterations,
                        tool=None,
                        ok=False,
                        extra={
                            "attempt": timeout_recovery_attempts,
                            "kind": type(e).__name__,
                        },
                    )
                    if progress:
                        progress.info(
                            f"Bedrock {type(e).__name__}; retrying same iteration "
                            f"({timeout_recovery_attempts}/{_MAX_BEDROCK_TIMEOUT_RECOVERIES})."
                        )
                    iterations -= 1
                    continue
                err_msg = (
                    f"{type(e).__name__}: {e}. Increase UIPATH_BEDROCK_READ_TIMEOUT "
                    f"(current {_bedrock_read_timeout_seconds()}s) or shorten the prompt."
                )
                if progress:
                    progress.error(err_msg)
                err_result = AgenticResult(
                    success=False,
                    final_response="",
                    tool_calls_made=tool_calls_made,
                    iterations=iterations,
                    files_written=files_written,
                    error=f"LLM call failed: {err_msg}",
                    tool_success_count=tool_success_count,
                    tool_failure_count=tool_failure_count,
                    tokens_in=tokens_in_total,
                    tokens_out=tokens_out_total,
                )
                self._record_learning(skill_name, user_request, err_result)
                return err_result
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
                err_msg = str(e)
                if "on-demand throughput isn" in err_msg:
                    from uipath_claude.llm.router import (
                        inference_profile_hint,
                        requires_inference_profile,
                        select_model_for_task,
                    )

                    current = select_model_for_task(
                        "agentic_executor",
                        ComplexitySignals(intent="build", planner_triggered=True),
                    )
                    if requires_inference_profile(current):
                        err_msg = f"{err_msg}\n\nHint: {inference_profile_hint(current)}"
                if progress:
                    progress.error(err_msg)
                err_result = AgenticResult(
                    success=False,
                    final_response="",
                    tool_calls_made=tool_calls_made,
                    iterations=iterations,
                    files_written=files_written,
                    error=f"LLM call failed: {err_msg}",
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
                    and plan_tool_nudges < 8
                    and iterations < max_iter
                ):
                    plan_tool_nudges += 1
                    messages.append(response)
                    nudge = (
                        f"SYSTEM: Your skill instructions include `{PLAN_BLOCK_HEADING}`. "
                        "Reading files is NOT executing the plan. You MUST now start "
                        "writing code.\n\n"
                        "For every XAML file in the plan, call `create_xaml_workflow` "
                        "(NOT write_file) with a JSON spec — root, arguments, variables, "
                        "body. Then call `validate_xaml` on each. Then "
                        "`uipath_workflow_build_and_verify` until verdict='pass'.\n\n"
                        "Do NOT finish with prose. Do NOT ask questions. Do NOT summarize. "
                        "Call `create_xaml_workflow` for the first workflow in the plan NOW. "
                        f"(Nudge {plan_tool_nudges}/8 — after this I will fail the run.)"
                    )
                    messages.append(HumanMessage(content=nudge))
                    if progress:
                        progress.info(
                            "Approved plan present but no write/validation/deploy-class tool yet; "
                            f"requesting tool calls ({plan_tool_nudges}/8)."
                        )
                    continue

                if (
                    contains_plan_block(skill_content)
                    and not _has_executed_plan(tool_calls_made)
                    and plan_tool_nudges >= 8
                ):
                    err_msg = (
                        "Executor failed: an approved plan was present but the "
                        "agent refused to call any write tool (create_xaml_workflow, "
                        "write_file, etc.) after 8 nudges. The plan was never "
                        "executed. No files were created."
                    )
                    if progress:
                        progress.error(err_msg)
                    err_result = AgenticResult(
                        success=False,
                        final_response=final_text,
                        tool_calls_made=tool_calls_made,
                        iterations=iterations,
                        files_written=files_written,
                        error=err_msg,
                        tool_success_count=tool_success_count,
                        tool_failure_count=tool_failure_count,
                        tokens_in=tokens_in_total,
                        tokens_out=tokens_out_total,
                    )
                    self._record_learning(skill_name, user_request, err_result)
                    return err_result

                if (
                    _build_verify_tool_available(tool_map)
                    and _has_mutated_project(tool_calls_made)
                    and verify_nudges < 5
                    and iterations < max_iter
                ):
                    passed, reason = _last_build_verify_was_pass(messages)
                    if not passed:
                        verify_nudges += 1
                        messages.append(response)
                        verify_instruction = (
                            "SYSTEM: You mutated the project but the verify gate "
                            "is not satisfied: "
                            f"{reason}. Call uipath_workflow_build_and_verify "
                            "for this project_dir and KEEP CALLING IT until the "
                            "result reports verdict='pass'. Required pipeline "
                            "(in order, ALL must pass): "
                            "(1) `uip rpa get-errors --min-severity error` clean — pass 1, "
                            "(2) `uip rpa get-errors --min-severity error` clean — pass 2 "
                            "(guards against the Studio IPC stale-cache failure mode), "
                            "(3) `uip rpa run-file --command StartExecution` exit 0 "
                            "(headless run), "
                            "(4) when Studio is detected: `uip rpa run-file --command "
                            "StartDebugging --use-studio` exit 0 (attached debug). "
                            "If Studio is unavailable the call returns "
                            "verdict='needs_human' with "
                            "next_action='start_studio_or_waive' — surface that "
                            "to the user and ASK whether to start Studio or "
                            "explicitly waive with require_studio_debug=false. "
                            "If the design gate or session gate returns "
                            "[BLOCKED], propose / approve the design or fix "
                            "the dirty files and re-verify before claiming "
                            "the task is complete. Do NOT finish with prose only."
                        )
                        messages.append(HumanMessage(content=verify_instruction))
                        if progress:
                            progress.info(
                                "Project mutated but build_and_verify has not "
                                f"reached verdict='pass' ({verify_nudges}/5)."
                            )
                        continue

                if _has_blocked_observation(messages) and verify_nudges < 5 and iterations < max_iter:
                    verify_nudges += 1
                    messages.append(response)
                    blocked_instruction = (
                        "SYSTEM: A recent tool call returned [BLOCKED] from "
                        "the MCP gate (session or design). You cannot finish "
                        "until the gate is cleared. Inspect the [BLOCKED] "
                        "message, then either: (a) propose+approve a design "
                        "via uipath_design_propose / uipath_design_approve, "
                        "or (b) call uipath_workflow_build_and_verify until "
                        "verdict='pass'. Do NOT report success while a "
                        "[BLOCKED] is the most recent tool result."
                    )
                    messages.append(HumanMessage(content=blocked_instruction))
                    if progress:
                        progress.info(
                            "Recent [BLOCKED] from MCP gate; requesting "
                            f"resolution ({verify_nudges}/5)."
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
                        design_blocked=design_blocked,
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
                redirect_project_dir: str | None = None
                if (
                    preflight_project_dir
                    and tool_name in _WRITE_INTENT_TOOL_NAMES
                ):
                    target_dir = (
                        _extract_project_dir_from_tool_args(tool_args)
                        or preflight_project_dir
                    )
                    try:
                        from uipath_claude.tools import design_store

                        gate_open = design_store.has_approved(target_dir)
                    except Exception:
                        gate_open = False
                    if not gate_open:
                        redirect_project_dir = target_dir

                if redirect_project_dir is not None:
                    result = _redirect_to_design_propose(
                        redirect_project_dir, tool_name
                    )
                    success = False
                    design_blocked = True
                elif self.approval is not None and not self.approval.check(tool_name, tool_args):
                    result = "[ERROR] Tool call blocked by approval policy."
                    success = False
                elif tool is None:
                    alias_target = _DESIGN_TOOL_ALIASES.get(tool_name)
                    if alias_target is not None:
                        result = _design_alias_message(tool_name, alias_target)
                    else:
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

                if not success and isinstance(result, str) and result.startswith(
                    "[ERROR] Unknown tool"
                ):
                    consecutive_unknown_tool += 1
                else:
                    consecutive_unknown_tool = 0

                if (
                    "[BLOCKED]" in result
                    and "no approved design" in result.lower()
                ):
                    design_blocked = True

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

            # Guard against infinite unknown-tool loops (common when LLM
            # hallucinates executor tool names in the planner phase). After
            # 3 consecutive unknown-tool errors, inject a strong nudge and
            # after 5, bail out with whatever plan text we have so far.
            if consecutive_unknown_tool >= 5:
                if progress:
                    progress.error(
                        "Aborting: 5 consecutive unknown-tool calls. "
                        "The agent is hallucinating tool names."
                    )
                final_text = (
                    "Planning aborted: the planner repeatedly tried to call tools "
                    "it does not have. Please retry the request."
                )
                # Try to salvage any assistant text already produced.
                for m in reversed(messages):
                    content = getattr(m, "content", None)
                    if isinstance(content, str) and content.strip() and not content.startswith("[ERROR]"):
                        final_text = content
                        break
                return AgenticResult(
                    final_response=final_text,
                    tool_calls_made=tool_calls_made,
                    files_written=files_written,
                    iterations=iterations,
                    success=False,
                    error="Aborted: repeated unknown-tool calls",
                    tool_success_count=tool_success_count,
                    tool_failure_count=tool_failure_count,
                    tokens_in=tokens_in_total,
                    tokens_out=tokens_out_total,
                    design_blocked=design_blocked,
                )
            if consecutive_unknown_tool in (1, 3):
                messages.append(
                    HumanMessage(
                        content=(
                            "STOP calling unknown tools. The tool you just tried DOES "
                            "NOT EXIST in this agent's tool set — re-read your system "
                            "prompt and use ONLY the tools it lists. If you want the "
                            "executor to call a tool, mention the tool name as TEXT "
                            "in your final markdown answer and STOP calling tools."
                        )
                    )
                )

            # One-shot budget extension: if we're about to exit and the
            # trailing window still shows progress, bump max_iter once.
            if (
                not _budget_extended
                and _iter_extend > 0
                and iterations >= max_iter
            ):
                tail = tool_calls_made[-5:]
                rolling_successes = sum(1 for c in tail if c.get("ok"))
                if rolling_successes >= 2:
                    max_iter += _iter_extend
                    _budget_extended = True
                    if progress:
                        progress.info(
                            f"[BUDGET_EXTENDED] reason=active_progress "
                            f"(+{_iter_extend} iterations, new cap={max_iter})"
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
        # Scope to ToolMessage only: the system prompt itself contains the
        # words "validation failed/error" / "error(s)" / "validate" verbatim,
        # so scanning every recent message produced false positives on short
        # message logs (e.g. right after a Bedrock ValidationException
        # recovery), causing an extra fake "fix validation" loop iteration.
        recent_messages = messages[-5:] if len(messages) >= 5 else messages

        for msg in recent_messages:
            if not isinstance(msg, ToolMessage):
                continue
            content = msg.content if isinstance(msg.content, str) else str(msg.content or "")
            content_lower = content.lower()
            if (
                ("validation failed" in content_lower
                 or "validation error" in content_lower
                 or "error(s)" in content_lower)
                and "validate" in content_lower
                and "0 error" not in content_lower
                and "passed" not in content_lower
            ):
                return True
            # MCP gate signals - the build_and_verify / session / design
            # gate emit these strings and the agent must not stop on them.
            if content.startswith("[BLOCKED]"):
                return True
            if (
                "verdict='needs_human'" in content_lower
                or '"verdict": "needs_human"' in content_lower
                or "verdict='needs_llm_fix'" in content_lower
                or '"verdict": "needs_llm_fix"' in content_lower
            ):
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
            "3. BEFORE writing any file into a UiPath project, propose a design "
            "via uipath_design_propose with a short user-facing summary, then "
            "ASK THE USER to approve via uipath_design_approve. Do not call "
            "write_file / install_package on a project until the design gate "
            "is open (no [BLOCKED] from uipath_workflow_*).",
            "4. After ANY mutation to a UiPath project (write_file, "
            "install_package, scaffolding) you MUST call "
            "uipath_workflow_build_and_verify and KEEP CALLING IT until the "
            "result reports verdict='pass'. The pipeline must include, in order: "
            "(a) `uip rpa get-errors --min-severity error` clean — pass 1, "
            "(b) `uip rpa get-errors --min-severity error` clean — pass 2 "
            "(the Studio IPC behind get-errors is stateful and a single pass "
            "can return a stale 'No diagnostics found' while real errors exist), "
            "(c) headless run exit 0 (`StartExecution`), "
            "(d) attached UiPath Studio debug exit 0 (`StartDebugging --use-studio`) "
            "when Studio is detected; otherwise verdict='needs_human' with "
            "next_action='start_studio_or_waive'. A single get-errors pass is "
            "NOT sufficient; the BUILD_LOG.md for the project must capture each "
            "step.",
            "5. CRITICAL: Do NOT stop, summarize, or claim the task is "
            "complete while ANY of the following are true: the most recent "
            "tool result starts with [BLOCKED]; build_and_verify_workflow "
            "returned verdict='needs_llm_fix' (fix the reported errors and "
            "re-call); build_and_verify_workflow returned verdict='needs_human' "
            "(typically Studio not running - surface the "
            "next_action='start_studio_or_waive' message to the user and ask "
            "whether to start Studio or explicitly waive with "
            "require_studio_debug=false); you have not called "
            "uipath_workflow_build_and_verify at least once after the last "
            "mutation. A static get-errors pass alone is NOT sufficient.",
            "6. Check project.json dependencies before using activities - install missing packages.",
            "7. If user requests deployment/publishing, use deploy_to_orchestrator AFTER build_and_verify reports verdict='pass'.",
            "8. When done AND verdict='pass': (a) if Studio had this project open "
            "(open-project, StartDebugging, or build_and_verify Studio steps), call "
            "`uip rpa close-project` for that project_dir (e.g. via run_uip_command) "
            "before you stop; (b) then summarize what was created/modified plus "
            "headless and Studio debug log excerpts from the final build_and_verify "
            "payload.",
            "9. For write_file and other session-scoped paths, use paths relative to the chat "
            "artifact root only — do not pass Windows absolute paths to write_file.",
            "10. Do not pass --use-studio to the uip CLI via run_uip_command; it is not "
            "supported on all CLI versions.",
            "11. NEVER edit project files via shell, ApplyPatch, or any path "
            "that bypasses uipath_workflow_write_file. The MCP detects "
            "out-of-band edits on the next gated call and will return "
            "[BLOCKED] until you re-run uipath_workflow_build_and_verify to "
            "verdict='pass'.",
            "",
            "## XAML AUTHORING — USE THE SPEC-BASED TOOL, NOT write_file",
            "",
            "For ANY new .xaml workflow, you MUST use `create_xaml_workflow` "
            "with a JSON spec (root, arguments, variables, body). It emits "
            "correct namespaces, `TextExpression.Language`, ViewState IDs, "
            "and C#/VB argument wrapping that hand-written XAML almost "
            "always gets wrong. Do NOT hand-author XAML via write_file — "
            "that path caused the recent `uipcli analyze` 11-error failures "
            "(missing `xmlns:s`, `xmlns:scg`, wrong expression language).",
            "After creating a XAML, call `validate_xaml` on it, then the "
            "normal build_and_verify pipeline. Only fall back to write_file "
            "for .json, .md, .cs, or surgical XAML patches on an already-"
            "validated file. If you catch yourself composing a full "
            "<Activity>...</Activity> string, STOP and use create_xaml_workflow.",
            "",
            "The `uipath-rpa` SKILL.md (in SKILL INSTRUCTIONS below) is "
            "authoritative for RPA project conventions: read its 'Critical "
            "Rules' section and the XAML references before emitting files.",
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
        if context.get("orchestration_route"):
            parts.append(f"Orchestration route: {context['orchestration_route']}")
        if context.get("orchestration_rationale"):
            r = str(context["orchestration_rationale"])
            if len(r) > 2000:
                r = r[:2000] + "..."
            parts.append("Orchestration rationale (from chat router):")
            parts.append(r)
            parts.append(
                "The chat orchestration step already selected this path; execute the "
                "user request with tools. Do not substitute a canned documentation or "
                "UiPlan-only flow unless the user request explicitly requires it."
            )
        
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
