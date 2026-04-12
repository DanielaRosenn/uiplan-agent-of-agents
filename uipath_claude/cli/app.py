"""CLI application entry point."""
import asyncio
from datetime import datetime, timezone
import os
import re
from pathlib import Path
import uuid

import typer
from uipath_claude.commands.analyze import register_analyze_command
from uipath_claude.commands.bootstrap import register_bootstrap_command
from uipath_claude.commands.help import register_help_command
from uipath_claude.commands.repair_restore import register_repair_restore_command
from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.skills import register_skills_command
from uipath_claude.commands.status import register_status_command
from uipath_claude.commands.update_skills import register_update_skills_command
from uipath_claude.commands.validate import register_validate_command
from uipath_claude.context.project import detect_uipath_project
from uipath_claude.memory.loader import load_memory
from uipath_claude.artifacts.materialize import (
    contains_file_blocks,
    materialize_from_assistant_text,
    validate_generated_project,
)
from uipath_claude.query.bootstrap import run_bootstrap_flow
from uipath_claude.query.conversation import ConversationEngine
from uipath_claude.query.router import route_user_input
from uipath_claude.rendering.branding import print_welcome_banner
from uipath_claude.skills.loader import load_skill_content
from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.skills.updater import check_for_updates
from uipath_claude.hooks.session_hooks import check_uip_installed
from uipath_claude.tools.skill_tool import create_skill_tool


app = typer.Typer(help="UiPath Claude Code - Conversational AI for UiPath")

_UIPATH_CHAT_SYSTEM = """You are UiPath Claude Code. You build UiPath Studio automations (workflow XAML), not WPF desktop apps, unless the user explicitly asks for WPF.

If a UiPath project already exists, do not regenerate scaffold files (`project.json`, `project.uiproj`, `.local`, `.objects`) unless the user explicitly asks.
When the user asks for a workflow, default to writing only `.xaml` workflow files.
Do not invent or pin legacy dependency versions in `project.json`; if package changes are required, explain the `uip rpa install-or-update-packages` command instead.

When the user asks you to CREATE, WRITE, or GENERATE files, you MUST include one or more file blocks using EXACTLY this format (markers on their own lines; path uses forward slashes only):

<<<UIPATH_FILE path="Main.xaml">>>
...complete file body...
<<<END_UIPATH_FILE>>>

Put files under logical subpaths (e.g. `demo/Main.xaml`). Use only relative paths; no `..` segments.
You may instead use a markdown code fence whose first line is exactly: path: <relative/path> then the file body on following lines until the closing fence.

After the blocks you may add one short sentence summarizing what you wrote."""

_SKILL_CONTEXT_MAX_CHARS = 8000
_SKILL_CONTEXT_MAX_ITEMS = 2
_RPA_HINT_TOKENS = {
    "uipath",
    "workflow",
    "workflows",
    "xaml",
    "automation",
    "outlook",
    "email",
    "excel",
    "browser",
    "selector",
    "queue",
    "mail",
}
_DOC_INTENT_TOKENS = {"pdd", "sdd", "document", "architecture", "design"}
_PROJECT_FILE_HINTS = {
    "project.json",
    "project.uiproj",
    "create project",
    "new project",
    "scaffold",
    "template",
}
_FILE_INTENT_TOKENS = {
    "build",
    "create",
    "generate",
    "write",
    "make",
    "workflow",
    "xaml",
    "project",
    "file",
    "files",
}


def _tokenize(text: str) -> set[str]:
    """Tokenize text for lightweight lexical scoring."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score_skill(skill: dict, user_input: str, user_tokens: set[str]) -> int:
    """Compute simple lexical relevance between user prompt and skill metadata."""
    name = str(skill.get("name", ""))
    description = str(skill.get("description", ""))
    triggers = skill.get("triggers", [])
    lower_input = user_input.lower()

    score = 0
    score += len(_tokenize(name) & user_tokens) * 4
    score += len(_tokenize(description) & user_tokens) * 2

    if isinstance(triggers, list):
        for trigger in triggers:
            trig = str(trigger).strip().lower()
            if not trig:
                continue
            if trig in lower_input:
                score += 6
            else:
                score += len(_tokenize(trig) & user_tokens)

    is_coded_intent = (
        ".cs" in lower_input
        or "coded workflow" in lower_input
        or "c#" in lower_input
        or ("coded" in user_tokens and "workflow" in user_tokens)
    )
    
    is_doc_intent = bool(user_tokens & _DOC_INTENT_TOKENS)

    if name == "uipath-coded-workflows" and is_coded_intent:
        score += 20
    elif name == "pdd-creation" and ("pdd" in user_tokens or "process definition" in lower_input):
        score += 20
    elif name == "sdd-flow-canvas" and ("sdd" in user_tokens or "solution design" in lower_input):
        score += 20
    elif name == "uipath-rpa-workflows":
        if is_coded_intent or is_doc_intent:
            score -= 10
        elif user_tokens & _RPA_HINT_TOKENS:
            score += 12

    return score


def _is_workflow_intent(user_input: str, user_tokens: set[str]) -> bool:
    """Detect likely RPA workflow requests."""
    lower = user_input.lower()
    if ".cs" in lower or "coded workflow" in lower:
        return False
    has_explicit_workflow_terms = bool({"workflow", "workflows", "xaml"} & user_tokens)
    if not has_explicit_workflow_terms and (user_tokens & _DOC_INTENT_TOKENS):
        return False
    if has_explicit_workflow_terms:
        return True
    return bool(user_tokens & _RPA_HINT_TOKENS)


def _select_relevant_skills(user_input: str, skills: list[dict], max_items: int = 2) -> list[dict]:
    """Select the most relevant skills for a free-form chat request."""
    user_tokens = _tokenize(user_input)
    if not user_tokens:
        return []

    ranked: list[tuple[int, dict]] = []
    for skill in skills:
        score = _score_skill(skill, user_input, user_tokens)
        if score <= 0:
            continue
        ranked.append((score, skill))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = [skill for _, skill in ranked[:max_items]]

    if _is_workflow_intent(user_input, user_tokens):
        rpa_skill = next((s for s in skills if s.get("name") == "uipath-rpa-workflows"), None)
        if rpa_skill and rpa_skill not in selected:
            selected = [rpa_skill, *selected][:max_items]
        elif rpa_skill in selected:
            selected = [rpa_skill, *[s for s in selected if s is not rpa_skill]][:max_items]

    return selected


def _debug_skill_selection(user_input: str, skills: list[dict]) -> list[str]:
    """Return human-readable skill score traces for diagnostics."""
    user_tokens = _tokenize(user_input)
    scored: list[tuple[int, str]] = []
    for skill in skills:
        scored.append((_score_skill(skill, user_input, user_tokens), str(skill.get("name", ""))))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [f"{name}: {score}" for score, name in scored[:5] if score > 0]


def _build_runtime_skill_context(user_input: str, skills: list[dict]) -> str:
    """Build request-scoped skill guidance injected into the model prompt."""
    selected = _select_relevant_skills(
        user_input, skills, max_items=_SKILL_CONTEXT_MAX_ITEMS
    )
    if not selected:
        return ""

    sections: list[str] = [
        "Use the following skill guidance for this request. Follow these rules strictly."
    ]
    for skill in selected:
        name = str(skill.get("name", "unknown"))
        content = load_skill_content(str(skill.get("path", "")))
        if not content:
            continue
        trimmed = content[:_SKILL_CONTEXT_MAX_CHARS]
        sections.append(f"[Skill: {name}]\n{trimmed}")

    return "\n\n".join(sections)


def _make_chat_session_id() -> str:
    """Create a traceable chat session identifier."""
    override = os.environ.get("UIPATH_CHAT_SESSION_ID", "").strip()
    if override:
        safe = re.sub(r"[^A-Za-z0-9._-]", "-", override)
        return safe or "chat-session"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _allow_project_file_generation(user_input: str) -> bool:
    """Only allow chat writes for project files when explicitly requested."""
    lower = user_input.lower()
    return any(hint in lower for hint in _PROJECT_FILE_HINTS)


def _is_file_generation_intent(user_input: str) -> bool:
    """Detect whether the user likely expects generated files."""
    tokens = _tokenize(user_input)
    return bool(tokens & _FILE_INTENT_TOKENS)


def _resolve_output_mode() -> str:
    """
    Resolve chat output mode for assistant responses.

    Modes:
    - auto: suppress file-heavy responses
    - quiet: always suppress assistant body
    - full: always print assistant body
    """
    mode = os.environ.get("UIPATH_CHAT_OUTPUT_MODE", "auto").strip().lower()
    if mode in {"quiet", "full"}:
        return mode
    return "auto"


def _is_generated_chat_artifact_folder(path: Path) -> bool:
    """Identify generated/chat output folders to prevent project-open confusion."""
    normalized = [part.lower() for part in path.resolve().parts]
    for index, part in enumerate(normalized):
        if part == "generated" and index + 1 < len(normalized) and normalized[index + 1] == "chat":
            return True
    return False


def _build_command_registry(
    skill_registry: SkillRegistry,
    get_status,
) -> CommandRegistry:
    """Create and register built-in slash commands."""
    registry = CommandRegistry()
    register_help_command(registry)
    register_status_command(registry, get_status=get_status)
    register_skills_command(
        registry,
        list_skills=skill_registry.load_skills,
        filter_skills_by_role=skill_registry.filter_by_agent,
    )
    register_analyze_command(registry)
    register_validate_command(registry)
    register_repair_restore_command(registry)
    register_bootstrap_command(registry, run_bootstrap=run_bootstrap_flow)
    register_update_skills_command(registry)
    return registry


def _create_engine() -> ConversationEngine:
    """Create Bedrock conversation engine from environment settings."""
    model_name = os.getenv(
        "UIPATH_CLAUDE_MODEL",
        "anthropic.claude-3-sonnet-20240229-v1:0",
    )
    region = os.getenv("AWS_REGION", "us-east-1")
    return ConversationEngine(model_name=model_name, region=region)


async def _get_model_response(
    engine: ConversationEngine,
    history: list[dict[str, str]],
    memory: str,
    runtime_context: str = "",
    *,
    stream: bool = False,
    on_delta=None,
) -> str:
    """Get an LLM response from Bedrock conversation engine."""
    base = _UIPATH_CHAT_SYSTEM
    context_parts = [base]
    if memory:
        context_parts.append(f"Memory:\n{memory}")
    if runtime_context:
        context_parts.append(f"Runtime guidance:\n{runtime_context}")
    context_prompt = "\n\n".join(context_parts)
    messages = [{"role": "system", "content": context_prompt}, *history]
    if stream:
        return await engine.run_stream(
            messages=messages,
            tools=[],
            system_prompt=context_prompt,
            on_delta=on_delta,
        )
    return await engine.run(messages=messages, tools=[], system_prompt=context_prompt)


@app.command()
def chat(
    no_banner: bool = typer.Option(False, "--no-banner", help="Skip welcome banner"),
    stream: bool | None = typer.Option(
        None,
        "--stream/--no-stream",
        help="Stream assistant tokens while generating responses.",
    ),
):
    """Start conversational chat mode."""
    if not no_banner:
        print_welcome_banner()
    
    project_context = detect_uipath_project(str(Path.cwd()))
    if project_context:
        print(f"Detected UiPath project: {project_context['project_name']}\n")
    cwd = Path.cwd().resolve()
    if _is_generated_chat_artifact_folder(cwd) and (cwd / "project.json").exists():
        print(
            "Warning: this looks like a generated chat artifact folder. "
            "Open your real UiPath project root for package restore/build.\n"
        )
    
    memory = load_memory(
        project_path=project_context["project_path"] if project_context else None
    )

    # Check for skills updates (non-blocking)
    try:
        has_updates, update_msg, _, _ = check_for_updates()
        if has_updates:
            print(f"Skills update available. Run /update-skills to update.\n")
    except Exception:
        pass  # Don't block startup on update check failures
    
    # Check uip CLI installation
    try:
        uip_ok, uip_msg = check_uip_installed()
        if not uip_ok:
            print(f"Warning: {uip_msg}\n")
    except Exception:
        pass
    
    skill_registry = SkillRegistry()
    model_name = os.getenv(
        "UIPATH_CLAUDE_MODEL",
        "anthropic.claude-3-sonnet-20240229-v1:0",
    )
    region = os.getenv("AWS_REGION", "us-east-1")
    skills = skill_registry.load_skills()
    skills_by_name = {skill.get("name"): skill for skill in skills}

    def _status() -> dict[str, str | int | bool]:
        return {
            "model": model_name,
            "region": region,
            "project_detected": bool(project_context),
            "project_name": project_context["project_name"] if project_context else "n/a",
            "memory_loaded": bool(memory),
            "skill_count": len(skills),
        }

    registry = _build_command_registry(skill_registry, _status)

    try:
        engine = _create_engine()
    except Exception as exc:
        print("Could not initialize Bedrock model.")
        print(
            "Set AWS credentials and region, then retry. "
            "Example: set AWS_REGION=us-east-1."
        )
        raise typer.Exit(code=1) from exc

    print("Chat session started. Type 'exit' or 'quit' to leave.\n")
    history: list[dict[str, str]] = []
    stream_enabled = _resolve_stream_enabled(stream)
    output_mode = _resolve_output_mode()
    chat_session_id = _make_chat_session_id()
    print(f"Chat trace id: {chat_session_id}\n")

    while True:
        try:
            user_input = typer.prompt("You").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        route, payload = route_user_input(user_input)
        if route == "command":
            command = payload["command"]
            args = payload["args"]
            if command == "chat":
                print("You are already in chat mode.")
                continue
            if command in {"exit", "quit"}:
                print("Goodbye!")
                break
            print(registry.execute(command, *args))
            continue
        if route == "skill_usage":
            print("Usage: /skill <skill-name> <query>")
            continue
        if route == "skill":
            skill_name = payload["skill_name"]
            query = payload["query"]
            skill = skills_by_name.get(skill_name)
            if not skill:
                print(f"Unknown skill: {skill_name}")
                continue
            tool = create_skill_tool(skill)
            result = tool.invoke({"query": query})
            print(f"Assistant: {result}\n")
            continue

        history.append({"role": "user", "content": user_input})
        runtime_context = _build_runtime_skill_context(user_input, skills)
        allow_project_files = _allow_project_file_generation(user_input)
        file_intent = _is_file_generation_intent(user_input)
        if os.environ.get("UIPATH_CHAT_DEBUG_SKILLS", "0").strip().lower() in {"1", "true", "yes"}:
            traces = _debug_skill_selection(user_input, skills)
            if traces:
                print("Skill selection:")
                for trace in traces:
                    print(f"  - {trace}")
                print("")
        try:
            if stream_enabled:
                suppress_stream_output = output_mode == "quiet" or (
                    output_mode == "auto" and file_intent
                )
                emitted_deltas = False

                if suppress_stream_output:
                    print("Assistant: Generating files, one moment...\n")

                def _print_delta(delta: str) -> None:
                    nonlocal emitted_deltas
                    emitted_deltas = True
                    print(delta, end="", flush=True)

                delta_callback = None if suppress_stream_output else _print_delta
                if not suppress_stream_output:
                    print("Assistant: ", end="", flush=True)

                response = asyncio.run(
                    _get_model_response(
                        engine,
                        history,
                        memory,
                        runtime_context,
                        stream=True,
                        on_delta=delta_callback,
                    )
                )
                if not emitted_deltas and not suppress_stream_output:
                    print(str(response), end="", flush=True)
                if not suppress_stream_output:
                    print("")
            else:
                response = asyncio.run(
                    _get_model_response(
                        engine,
                        history,
                        memory,
                        runtime_context,
                        stream=False,
                    )
                )
        except Exception as exc:
            print("Bedrock request failed.")
            print(
                "Check AWS credentials, IAM permissions, model access, and AWS_REGION. "
                f"Details: {exc}"
            )
            continue

        history.append({"role": "assistant", "content": str(response)})

        response_has_files = contains_file_blocks(str(response))
        suppress_output = output_mode == "quiet" or (
            output_mode == "auto" and response_has_files
        )
        if not stream_enabled:
            if suppress_output:
                print("Assistant: Generating files, one moment...\n")
            else:
                print(f"Assistant: {response}\n")
        elif not suppress_output and not file_intent:
            print("")

        if os.environ.get("UIPATH_CHAT_MATERIALIZE", "1").lower() not in (
            "0",
            "false",
            "no",
        ):
            chat_output_base = Path(
                os.environ.get(
                    "UIPATH_CHAT_OUTPUT_DIR",
                    str(Path.cwd() / "generated" / "chat"),
                )
            ).resolve()
            chat_root = chat_output_base / chat_session_id
            written = materialize_from_assistant_text(
                str(response),
                output_root=chat_root,
                allow_project_files=allow_project_files,
            )
            if written:
                print("Wrote:")
                for path in written:
                    print(f"  {path}")
                print("")
                
                has_xaml = any(str(p).endswith(".xaml") for p in written)
                auto_validate = os.environ.get("UIPATH_CHAT_AUTO_VALIDATE", "1").lower() not in ("0", "false", "no")
                
                if has_xaml and auto_validate:
                    print("Validating generated workflow...")
                    validation = validate_generated_project(chat_root)
                    if validation["success"]:
                        print("Validation: PASSED - No errors found\n")
                    else:
                        print(f"Validation: FAILED - {len(validation['errors'])} error(s)")
                        for error in validation["errors"][:5]:
                            print(f"  - {error}")
                        if len(validation["errors"]) > 5:
                            print(f"  ... and {len(validation['errors']) - 5} more")
                        print("")
                        print("The generated workflow has errors. Consider asking the agent to fix them.\n")
                
                if not allow_project_files:
                    print(
                        "Note: generated files are artifacts. "
                        "Use a real UiPath project root for full package restore/publish.\n"
                    )


def _resolve_stream_enabled(stream_flag: bool | None) -> bool:
    """Resolve stream mode from CLI flag and environment."""
    if stream_flag is not None:
        return stream_flag
    env = os.environ.get("UIPATH_CHAT_STREAM", "1").strip().lower()
    return env not in {"0", "false", "no"}


@app.command()
def start_project(
    project_name: str = typer.Argument(..., help="Project name"),
):
    """Run full bootstrap flow (BA/SA/Dev/QA) and write artifacts to cwd."""
    from uipath_claude.query.engine_factory import create_conversation_engine_from_env

    request = f"New UiPath automation project named {project_name}"
    print(f"Starting bootstrap for: {project_name}\n")
    try:
        engine = create_conversation_engine_from_env()
    except Exception as exc:
        print("Could not initialize Bedrock model for bootstrap.")
        print(f"Details: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        result = asyncio.run(
            run_bootstrap_flow(request, engine=engine, output_root=Path.cwd())
        )
    except Exception as exc:
        print(f"Bootstrap failed: {exc}")
        raise typer.Exit(code=1) from exc

    print("Bootstrap complete. Artifact paths:")
    for key, val in sorted((result.get("paths") or {}).items()):
        print(f"  {key}: {val}")


if __name__ == "__main__":
    app()
