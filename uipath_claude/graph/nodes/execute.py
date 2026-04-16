"""Execute node with optional agentic tool-use loop."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from uipath_claude.query.feedback_loop import detect_clarifying_question


def make_execute_node(
    skills_by_name: dict[str, dict[str, Any]],
    build_runtime_for_selected: Callable[[str, list[dict[str, Any]]], str],
    run_model: Callable[
        [list[dict[str, str]], str, bool], Awaitable[str]
    ],
    *,
    default_stream: bool = False,
    agentic_tools: list | None = None,
    model_name: str | None = None,
    region: str | None = None,
    approval: Any | None = None,
    session_logging: tuple[Any, str] | None = None,
) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    """Create the execute node.

    Args:
        skills_by_name: Mapping of skill name to skill dict
        build_runtime_for_selected: Function to build runtime context
        run_model: Function to call LLM (single-shot mode)
        default_stream: Whether to stream by default
        agentic_tools: Optional list of tools for agentic execution
        model_name: Model name for agentic execution
        region: AWS region for agentic execution

    Returns:
        Async execute node function
    """
    async def execute_node(state: dict[str, Any]) -> dict[str, Any]:
        messages = list(state.get("messages") or [])
        if not messages:
            return {"assistant_response": "", "pending_question": None, "phase": "complete"}
        last = messages[-1]
        if last.get("role") != "user":
            return {"assistant_response": "", "pending_question": None, "phase": "complete"}
        
        user_input = str(last.get("content", ""))
        names = state.get("selected_skill_names") or []
        selected = [skills_by_name[n] for n in names if n in skills_by_name]
        runtime = build_runtime_for_selected(user_input, selected)
        extra = str(state.get("runtime_extra") or "").strip()
        if extra:
            runtime = f"{runtime}\n\n{extra}".strip() if runtime else extra
        
        # Check if agentic mode is enabled
        use_agentic = (
            agentic_tools
            and model_name
            and region
            and os.environ.get("UIPATH_AGENTIC_MODE", "1").lower() in ("1", "true", "yes")
        )
        
        if use_agentic and agentic_tools:
            # Run with agentic tool-use loop
            from uipath_claude.query.agentic_executor import AgenticExecutor
            from uipath_claude.sessions.store import SessionEvent

            def _on_tool_result(tool_name: str, res: str) -> None:
                if not session_logging:
                    return
                store, sid = session_logging
                try:
                    ok = isinstance(res, str) and res.startswith("[OK]")
                    store.append(sid, SessionEvent(kind="tool", name=tool_name, text=res[:8000], ok=ok))
                except Exception:
                    return

            executor = AgenticExecutor(
                model_name=model_name,
                region=region,
                approval=approval,
                on_tool_result=_on_tool_result if session_logging else None,
            )
            
            project_context = {
                "output_dir": os.environ.get("UIPATH_CHAT_OUTPUT_DIR", ""),
                "session_id": os.environ.get("UIPATH_CHAT_SESSION_ID", ""),
                "selected_skill_names": list(names),
            }
            
            primary_skill = names[0] if names else "unknown"
            result = await executor.execute(
                skill_content=runtime,
                user_request=user_input,
                tools=agentic_tools,
                project_context=project_context,
                skill_name=primary_skill,
            )
            
            if result.success:
                text = result.final_response
                if result.tool_failure_count > 0:
                    total = result.tool_success_count + result.tool_failure_count
                    warn = (
                        f"\n\n**Tool errors:** {result.tool_failure_count} of {total} "
                        "tool call(s) returned messages containing errors or failures "
                        "(the agent still finished its loop). Check console debug output "
                        "for full tool text.\n"
                    )
                    text = warn + text
                # Add tool call summary if files were written
                if result.files_written:
                    files_summary = "\n".join(f"  - {f}" for f in result.files_written)
                    text = f"{text}\n\n**Files created:**\n{files_summary}"
                if project_context.get("output_dir") and project_context.get("session_id"):
                    root = (
                        Path(project_context["output_dir"]).expanduser().resolve()
                        / project_context["session_id"]
                    )
                    text = f"{text}\n\n**Artifact root:** `{root}`"
            else:
                text = f"Execution failed: {result.error or 'Unknown error'}"
                if result.tool_calls_made:
                    text += f"\n\nTool calls made: {len(result.tool_calls_made)}"
        else:
            # Single-shot mode (original behavior)
            stream = bool(state.get("stream", default_stream))
            response = await run_model(messages, runtime, stream)
            text = str(response)
        
        question = detect_clarifying_question(text)
        new_messages = [*messages, {"role": "assistant", "content": text}]
        return {
            "messages": new_messages,
            "assistant_response": text,
            "pending_question": question,
            "phase": "complete",
        }

    return execute_node
