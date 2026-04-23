import os

import typer

from tools.uiplan.scaffold.loop_runner import resolve_max_loops

app = typer.Typer(help="UiPlan runtime commands")


@app.command("generate-docs")
def generate_docs(plan_slug: str) -> None:
    print(f"generate-docs:{plan_slug}")


@app.command("scaffold-code")
def scaffold_code(
    plan_slug: str,
    max_loops: int | None = typer.Option(
        None,
        "--max-loops",
        help="Max validate/fix loops (1-25). Overrides UIPLAN_MAX_LOOPS. Default: 5.",
    ),
) -> None:
    effective = resolve_max_loops(
        flag_value=max_loops,
        env_value=os.environ.get("UIPLAN_MAX_LOOPS"),
    )
    print(f"scaffold-code:{plan_slug}:max_loops={effective}")
