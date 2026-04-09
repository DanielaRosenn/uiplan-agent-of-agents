"""CLI entry point for UiPath Builder Agent."""

import asyncio
import uuid
from pathlib import Path

import typer
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from agent import __version__ as VERSION
from agent.context.project_detector import detect_uipath_project
from agent.graph import graph, conversational_graph
from agent.memory.loader import load_memory, get_default_global_dir
from agent.nodes.hitl_node import format_hitl_display
from agent.rendering.message_renderer import render_message
from cli.branding import print_welcome_banner
from cli.commands import parse_slash_command, execute_command

MODEL = "claude-sonnet-4-20250514"

app = typer.Typer(
    name="uipath-builder",
    help="UiPath Builder Agent - AI-powered RPA project generator",
)


def _run_async(coro):
    """Run an async coroutine synchronously (fresh loop each call; safe on Windows)."""
    return asyncio.run(coro)


@app.command()
def start_project(
    description: str = typer.Option(
        None,
        "--description",
        "-d",
        help="Process description to bootstrap from",
    ),
    output_dir: str = typer.Option(
        "./output",
        "--output",
        "-o",
        help="Output directory for generated files",
    ),
):
    """Start the bootstrap flow: BA -> SA -> HITL -> Developer -> QA."""
    typer.echo("=" * 60)
    typer.echo("  UiPath Builder Agent - Bootstrap Flow")
    typer.echo("=" * 60)

    if not description:
        description = typer.prompt("\nDescribe the process you want to automate")

    thread_id = str(uuid.uuid4())
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    # Initial state with user's description
    initial_state = {
        "messages": [HumanMessage(content=description)],
        "mode": "bootstrap",
        "current_phase": "ba",
        "qa_iterations": 0,
    }

    typer.echo("\n[BA] Analyzing requirements...")

    # Run the graph - it will stop at HITL interrupt or run to completion
    try:
        result = _run_async(graph.ainvoke(initial_state, config))  # type: ignore
    except Exception as e:
        typer.echo(f"\nError during execution: {e}")
        raise typer.Exit(1)

    # Check if we stopped for HITL review
    snapshot = _run_async(graph.aget_state(config))
    if snapshot.next and "hitl" in snapshot.next:
        # Display SDD for review
        sdd = result.get("sdd", {})
        typer.echo(format_hitl_display(sdd))

        review = typer.prompt("Your review")

        # Resume with human response
        _run_async(
            graph.aupdate_state(
                config,
                {"messages": [HumanMessage(content=review)]},
            )
        )

        try:
            result = _run_async(graph.ainvoke(None, config))
        except Exception as e:
            typer.echo(f"\nError during HITL resume: {e}")
            raise typer.Exit(1)

    # Check if BA needs clarification
    if result.get("needs_clarification"):
        typer.echo("\n[BA] Clarification needed:")
        typer.echo(result.get("clarify_question", "Please provide more details."))
        answer = typer.prompt("\nYour answer")

        # Resume with clarification
        clarification_state = {
            "messages": [HumanMessage(content=answer)],
            "needs_clarification": False,
        }

        try:
            result = _run_async(graph.ainvoke(clarification_state, config))  # type: ignore
        except Exception as e:
            typer.echo(f"\nError during clarification: {e}")
            raise typer.Exit(1)

    # Display results
    _display_results(result, output_dir)


def _display_results(result: dict, output_dir: str):
    """Display final results and write artifacts to disk."""
    typer.echo("\n" + "=" * 60)

    # QA results
    qa_report = result.get("qa_report", {})
    if qa_report.get("passed"):
        typer.echo("  QA: PASSED")
    else:
        errors = result.get("validation_errors", [])
        if errors:
            typer.echo(f"  QA: FAILED ({len(errors)} errors)")
            for e in errors:
                typer.echo(f"    - {e}")
        else:
            typer.echo("  QA: No report available")

    # Write artifacts
    artifacts = result.get("artifacts", {})
    if artifacts:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        typer.echo(f"\n  Writing {len(artifacts)} files to {output_path}/")
        for filename, content in artifacts.items():
            file_path = output_path / filename
            file_path.write_text(content, encoding="utf-8")
            typer.echo(f"    - {filename}")

        typer.echo(f"\n  Project generated in: {output_path.resolve()}")
    else:
        typer.echo("\n  No artifacts were generated.")

    typer.echo("=" * 60)


@app.command()
def chat(
    no_banner: bool = typer.Option(
        False,
        "--no-banner",
        help="Suppress the welcome banner",
    ),
):
    """Start a conversational session with the agent."""
    cwd = Path.cwd()
    session_id = str(uuid.uuid4())
    thread_id = session_id
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    # Detect UiPath project
    project_context = detect_uipath_project(cwd)

    # Load memory
    memory = load_memory(global_dir=get_default_global_dir(), project_dir=cwd)

    # Print welcome banner (unless --no-banner)
    if not no_banner:
        project_name = project_context.name if project_context else None
        print_welcome_banner(
            version=VERSION,
            cwd=str(cwd),
            model=MODEL,
            project_name=project_name,
        )
    else:
        typer.echo("Type 'exit' or 'quit' to end the session")

    # Build initial state with new fields
    state: dict = {
        "messages": [],
        "mode": "conversational",
        "session_id": session_id,
        "memory_context": memory.content,
        "tool_calls_this_turn": 0,
        "tool_results": [],
    }
    if project_context:
        state["uipath_project"] = {
            "name": project_context.name,
            "project_id": project_context.project_id,
            "dependencies": project_context.dependencies,
        }
        state["uipath_workflows"] = project_context.workflows
        state["uipath_dependencies"] = project_context.dependencies

    while True:
        try:
            user_input = typer.prompt("\nYou")
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.strip().lower() in ("exit", "quit", "q"):
            typer.echo("Goodbye!")
            break

        # Check for slash commands
        parsed = parse_slash_command(user_input)
        if parsed:
            cmd_context = {
                "session_id": session_id,
                "model": MODEL,
                "cwd": str(cwd),
                "project_name": project_context.name if project_context else None,
                "project_path": str(project_context.project_path) if project_context else None,
                "skills_dir": str(cwd / "skills") if (cwd / "skills").exists() else None,
            }
            result = execute_command(parsed["command"], parsed["args"], cmd_context)
            typer.echo(f"\n{result}\n")
            continue

        # Regular message - send to agent
        state["messages"] = [HumanMessage(content=user_input)]

        try:
            result = _run_async(conversational_graph.ainvoke(state, config))  # type: ignore
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                rendered = render_message(last)
                typer.echo(f"\nAgent: {rendered}")
        except Exception as e:
            typer.echo(f"\nError: {e}")


if __name__ == "__main__":
    app()
