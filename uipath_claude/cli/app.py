"""CLI application entry point."""
import asyncio
import os
from pathlib import Path

import typer
from uipath_claude.commands.analyze import register_analyze_command
from uipath_claude.commands.bootstrap import register_bootstrap_command
from uipath_claude.commands.help import register_help_command
from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.skills import register_skills_command
from uipath_claude.commands.status import register_status_command
from uipath_claude.commands.validate import register_validate_command
from uipath_claude.context.project import detect_uipath_project
from uipath_claude.memory.loader import load_memory
from uipath_claude.artifacts.materialize import materialize_from_assistant_text
from uipath_claude.query.bootstrap import run_bootstrap_flow
from uipath_claude.query.conversation import ConversationEngine
from uipath_claude.query.router import route_user_input
from uipath_claude.rendering.branding import print_welcome_banner
from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.tools.skill_tool import create_skill_tool


app = typer.Typer(help="UiPath Claude Code - Conversational AI for UiPath")

_UIPATH_CHAT_SYSTEM = """You are UiPath Claude Code. You build UiPath Studio automations (workflow XAML, project.json), not WPF desktop apps, unless the user explicitly asks for WPF.

When the user asks you to CREATE, WRITE, or GENERATE files, you MUST include one or more file blocks using EXACTLY this format (markers on their own lines; path uses forward slashes only):

<<<UIPATH_FILE path="Main.xaml">>>
...complete file body...
<<<END_UIPATH_FILE>>>

Put files under logical subpaths (e.g. `demo/Main.xaml`). Use only relative paths; no `..` segments.
You may instead use a markdown code fence whose first line is exactly: path: <relative/path> then the file body on following lines until the closing fence.

After the blocks you may add one short sentence summarizing what you wrote."""


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
    register_bootstrap_command(registry, run_bootstrap=run_bootstrap_flow)
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
) -> str:
    """Get an LLM response from Bedrock conversation engine."""
    base = _UIPATH_CHAT_SYSTEM
    context_prompt = f"{base}\n\nMemory:\n{memory}" if memory else base
    messages = [{"role": "system", "content": context_prompt}, *history]
    return await engine.run(messages=messages, tools=[], system_prompt=base)


@app.command()
def chat(
    no_banner: bool = typer.Option(False, "--no-banner", help="Skip welcome banner"),
):
    """Start conversational chat mode."""
    if not no_banner:
        print_welcome_banner()
    
    project_context = detect_uipath_project(str(Path.cwd()))
    if project_context:
        print(f"Detected UiPath project: {project_context['project_name']}\n")
    
    memory = load_memory(
        project_path=project_context["project_path"] if project_context else None
    )

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
        try:
            response = asyncio.run(_get_model_response(engine, history, memory))
        except Exception as exc:
            print("Bedrock request failed.")
            print(
                "Check AWS credentials, IAM permissions, model access, and AWS_REGION. "
                f"Details: {exc}"
            )
            continue

        history.append({"role": "assistant", "content": str(response)})

        print(f"Assistant: {response}\n")

        if os.environ.get("UIPATH_CHAT_MATERIALIZE", "1").lower() not in (
            "0",
            "false",
            "no",
        ):
            chat_root = Path(
                os.environ.get(
                    "UIPATH_CHAT_OUTPUT_DIR",
                    str(Path.cwd() / "generated" / "chat"),
                )
            ).resolve()
            written = materialize_from_assistant_text(str(response), output_root=chat_root)
            if written:
                print("Wrote:")
                for path in written:
                    print(f"  {path}")
                print("")


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
