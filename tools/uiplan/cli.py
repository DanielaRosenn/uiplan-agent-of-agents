import typer

app = typer.Typer(help="UiPlan runtime commands")


@app.command("generate-docs")
def generate_docs(plan_slug: str) -> None:
    print(f"generate-docs:{plan_slug}")


@app.command("scaffold-code")
def scaffold_code(plan_slug: str, max_loops: int = 5) -> None:
    print(f"scaffold-code:{plan_slug}:max_loops={max_loops}")
