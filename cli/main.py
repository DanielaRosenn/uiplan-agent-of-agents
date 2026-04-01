"""CLI entry point for UiPath Builder Agent."""

import asyncio
import uuid
import json
from pathlib import Path

import typer
from langchain_core.messages import HumanMessage

from agent.graph import graph, conversational_graph
from agent.nodes.hitl_node import format_hitl_display

app = typer.Typer(
    name="uipath-builder",
    help="UiPath Builder Agent - AI-powered RPA project generator",
)


def _run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


@app.command()
def start_project(
    description: str = typer.Option(
        None,
        "--description", "-d",
        help="Process description to bootstrap from",
    ),
    output_dir: str = typer.Option(
        "./output",
        "--output", "-o",
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
    config = {"configurable": {"thread_id": thread_id}}

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
        result = _run_async(graph.ainvoke(initial_state, config))
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
        _run_async(graph.aupdate_state(
            config,
            {"messages": [HumanMessage(content=review)]},
        ))

        try:
            result = _run_async(graph.ainvoke(None, config))
        except Exception as e:
            typer.echo(f"\nError during HITL resume: {e}")
            raise typer.Exit(1)

    # Check if BA needs clarification
    if result.get("needs_clarification"):
        typer.echo(f"\n[BA] Clarification needed:")
        typer.echo(result.get("clarify_question", "Please provide more details."))
        answer = typer.prompt("\nYour answer")

        # Resume with clarification
        clarification_state = {
            "messages": [HumanMessage(content=answer)],
            "needs_clarification": False,
        }

        try:
            result = _run_async(graph.ainvoke(clarification_state, config))
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
def chat():
    """Start a conversational session with the agent."""
    typer.echo("=" * 60)
    typer.echo("  UiPath Builder Agent - Chat Mode")
    typer.echo("  Type 'exit' or 'quit' to end the session")
    typer.echo("=" * 60)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        try:
            user_input = typer.prompt("\nYou")
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.strip().lower() in ("exit", "quit", "q"):
            typer.echo("Goodbye!")
            break

        state = {
            "messages": [HumanMessage(content=user_input)],
            "mode": "conversational",
        }

        try:
            result = _run_async(conversational_graph.ainvoke(state, config))
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                content = last.content if hasattr(last, "content") else str(last)
                typer.echo(f"\nAgent: {content}")
        except Exception as e:
            typer.echo(f"\nError: {e}")


if __name__ == "__main__":
    app()
