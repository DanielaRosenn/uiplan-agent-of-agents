import os
from pathlib import Path

import typer

from tools.uiplan.generators.docs_bundle import default_kit_dir, generate_docs_bundle
from tools.uiplan.paradigms import KNOWN_PARADIGMS, normalize_paradigm
from tools.uiplan.scaffold.loop_runner import resolve_max_loops
from tools.uiplan.scaffold.runner import format_scaffold_stdout, run_scaffold
from tools.uiplan.validators.mermaid_mmdc import validate_mermaid_with_mmdc
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
        help="Template kit directory. Default: templates/uiplan under repo root.",
    ),
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="When strict (default), fail if visual-density checks do not pass.",
    ),
    paradigm: str | None = typer.Option(
        None,
        "--paradigm",
        help=(
            "Optional project paradigm override. "
            f"Known values: {', '.join(p for p in KNOWN_PARADIGMS if p != 'unknown')}."
        ),
    ),
) -> None:
    """Copy UiPlan kit templates into a folder with baseline placeholders filled."""
    repo = _repo_root()
    output = out or (repo / ".cursor" / "plans" / plan_slug)
    kit_dir = kit or default_kit_dir(repo)
    if paradigm is not None and normalize_paradigm(paradigm) == "unknown":
        typer.echo(
            "Unknown --paradigm value. Use one of: "
            + ", ".join(p for p in KNOWN_PARADIGMS if p != "unknown"),
            err=True,
        )
        raise typer.Exit(code=2)
    generate_docs_bundle(
        repo_root=repo,
        plan_slug=plan_slug,
        output_dir=output,
        kit_dir=kit_dir,
        paradigm=paradigm,
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
    repo: Path | None = typer.Option(
        None,
        "--repo",
        help="Repository root to classify (default: parent of tools/, i.e. this monorepo).",
    ),
) -> None:
    """Run scaffold checks for the detected project type (see docs/uiplan/SCAFFOLD_CODE.md)."""
    effective = resolve_max_loops(
        flag_value=max_loops,
        env_value=os.environ.get("UIPLAN_MAX_LOOPS"),
    )
    root = repo.resolve() if repo is not None else _repo_root()
    payload = run_scaffold(plan_slug=plan_slug, repo_root=root, max_loops=effective)
    typer.echo(format_scaffold_stdout(payload))
    outcome = payload.get("loop_outcome") or {}
    if outcome.get("status") != "ok":
        raise typer.Exit(code=1)


@app.command("validate-mermaid")
def validate_mermaid(
    paths: list[Path] = typer.Argument(
        ...,
        help="Markdown files to scan for ```mermaid fences.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    """Validate fenced Mermaid blocks using ``mmdc`` (optional; see docs/uiplan/MERMAID_VALIDATION.md)."""
    issues = validate_mermaid_with_mmdc(paths)
    if issues:
        for line in issues:
            typer.echo(line, err=True)
        raise typer.Exit(code=1)
    typer.echo("mermaid: OK")
