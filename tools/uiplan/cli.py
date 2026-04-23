import os
from pathlib import Path

import typer

from tools.uiplan.generators.docs_bundle import default_kit_dir, generate_docs_bundle
from tools.uiplan.scaffold.loop_runner import resolve_max_loops
from tools.uiplan.validators.visual_density import validate_uiplan_docs

app = typer.Typer(help="UiPlan runtime commands")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@app.command("generate-docs")
def generate_docs(
    plan_slug: str,
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Output directory for spec.md, plan.md, tasks.md. "
        "Default: .cursor/plans/<plan_slug>/",
    ),
    kit: Path | None = typer.Option(
        None,
        "--kit",
        help="Template kit directory. Default: docs/uiplan/kit under repo root.",
    ),
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="When strict (default), fail if visual-density checks do not pass.",
    ),
) -> None:
    """Copy UiPlan kit templates into a folder with baseline placeholders filled."""
    repo = _repo_root()
    output = out or (repo / ".cursor" / "plans" / plan_slug)
    kit_dir = kit or default_kit_dir(repo)
    generate_docs_bundle(
        repo_root=repo,
        plan_slug=plan_slug,
        output_dir=output,
        kit_dir=kit_dir,
    )
    issues = validate_uiplan_docs(output, strict=strict)
    if issues:
        for line in issues:
            typer.echo(line, err=True)
        if strict:
            raise typer.Exit(code=1)
    typer.echo(f"Wrote UiPlan docs to {output}")


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
