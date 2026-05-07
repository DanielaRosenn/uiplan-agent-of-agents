"""`uipath-claude explore` — boot the UiPlan Studio Explorer for a project.

This command launches the FastAPI backend (`services/uiplan-studio-api`) and
the Vite dev server (`apps/uiplan-studio`) as subprocesses in the same group,
opens the user's browser, and waits for Ctrl-C to shut both down cleanly.

Modes:

    uipath-claude explore                 # boot the studio for the current project
    uipath-claude explore --init          # write `.uiplan/explorer.yaml` and exit
    uipath-claude explore --check         # run the indexer and print a summary
    uipath-claude explore --no-browser    # boot but don't open a browser
    uipath-claude explore --port 5173     # custom Vite port

The frontend automatically passes the project path through to the backend via
`?worktree=<absolute-path>`, so the studio always opens to the right project.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

import typer


def _repo_root() -> Path:
    """Find the uipath-builder-agent checkout root by walking upwards."""
    start = Path(__file__).resolve()
    for parent in (start, *start.parents):
        if (parent / "apps" / "uiplan-studio").is_dir() and (parent / "services" / "uiplan-studio-api").is_dir():
            return parent
    # Fallback: 4 levels up from this file (framework/uipath_claude/cli/explore.py)
    return start.parents[3]


def _find_free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def _detect_project_dir(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).resolve()
        if not path.is_dir():
            raise typer.BadParameter(f"--project-dir does not exist: {path}")
        return path
    return Path.cwd().resolve()


def _print_indexer_summary(project: Path) -> None:
    """Run the indexer in-process and print a summary. Used by --check."""
    repo = _repo_root()
    backend_dir = repo / "services" / "uiplan-studio-api"
    sys.path.insert(0, str(backend_dir))
    from app.explorer_config import load_config  # type: ignore
    from app.explorer_indexer import index_project  # type: ignore
    from app.explorer_skills import aggregate_skill_graph_context  # type: ignore
    config = load_config(project)
    result = index_project(project, config)
    skill_nodes, skill_edges = aggregate_skill_graph_context(repo, result.nodes)
    typer.echo("")
    typer.echo(f"  project        : {config.project.name}")
    typer.echo(f"  type           : {config.project.type}")
    typer.echo(f"  config         : {config.source_path or '(defaults - no .uiplan/explorer.yaml found)'}")
    typer.echo(f"  files scanned  : {result.files_scanned}")
    typer.echo(f"  nodes          : {len(result.nodes) + len(skill_nodes)}")
    typer.echo(f"  edges          : {len(result.edges) + len(skill_edges)}")
    typer.echo(f"  skills         : {len(skill_nodes)}")
    typer.echo(f"  warnings       : {len(result.warnings)}")
    if result.warnings[:5]:
        typer.echo("  first warnings :")
        for w in result.warnings[:5]:
            typer.echo(f"      - {w}")
    layer_counts: dict[str, int] = {}
    for node in result.nodes:
        layer_counts[node["layer"]] = layer_counts.get(node["layer"], 0) + 1
    if skill_nodes:
        layer_counts["skills"] = len(skill_nodes)
    if layer_counts:
        typer.echo("  layers         :")
        for layer in sorted(layer_counts):
            typer.echo(f"      {layer:14s} {layer_counts[layer]:>4d}")
    typer.echo("")


def _do_init(project: Path) -> None:
    repo = _repo_root()
    sys.path.insert(0, str(repo / "services" / "uiplan-studio-api"))
    from app.explorer_config import (  # type: ignore
        ANNOTATIONS_FILENAME, CONFIG_DIRNAME, CONFIG_FILENAME, render_starter_config,
    )
    config_dir = project / CONFIG_DIRNAME
    config_path = config_dir / CONFIG_FILENAME
    if config_path.exists():
        typer.echo(f"already exists: {config_path} (no changes)")
        return
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_starter_config(project), encoding="utf-8")
    annotations_path = config_dir / ANNOTATIONS_FILENAME
    if not annotations_path.exists():
        annotations_path.write_text(
            "# Per-node overrides merged on top of the indexer output.\n"
            "# Keys are node ids (see `uipath-claude explore --check`).\n"
            "# Example:\n"
            "#   rpa:Main.xaml:\n"
            "#     business_status: live\n"
            "#     business_meta: { owner: Sales Ops, sla: \"p95 8 min\", risk: medium }\n",
            encoding="utf-8",
        )
    typer.echo(f"created: {config_path}")
    typer.echo(f"created: {annotations_path}")
    typer.echo("")
    typer.echo("Edit the file with your project's overview, then run:")
    typer.echo("    uipath-claude explore --check")


def _wait_for_port(port: int, *, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.25)
    return False


def _do_explore(project: Path, *, port: int, open_browser: bool) -> int:
    repo = _repo_root()
    backend_dir = repo / "services" / "uiplan-studio-api"
    frontend_dir = repo / "apps" / "uiplan-studio"

    if not backend_dir.is_dir() or not frontend_dir.is_dir():
        typer.echo(
            "error: could not locate the studio under this checkout.\n"
            "       Expected:\n"
            f"         {backend_dir}\n"
            f"         {frontend_dir}",
            err=True,
        )
        return 2

    api_port = _find_free_port(8000)
    web_port = _find_free_port(port)

    env = os.environ.copy()
    env["UIPATH_MCP_PROJECT_ROOT"] = str(project)
    env["VITE_UIPLAN_API_URL"] = f"http://127.0.0.1:{api_port}"

    typer.echo("")
    typer.echo(f"  project   : {project}")
    typer.echo(f"  api       : http://127.0.0.1:{api_port}")
    typer.echo(f"  studio    : http://127.0.0.1:{web_port}")
    typer.echo("")
    typer.echo("  starting backend …")

    # On Windows, start each subprocess in its own process group so that
    # `signal.CTRL_BREAK_EVENT` reaches only the child and not the parent
    # shell. On POSIX this flag does not exist; `creationflags=0` is a no-op.
    popen_creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0  # type: ignore[attr-defined]

    backend_cmd = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", str(api_port), "--log-level", "warning",
    ]
    backend = subprocess.Popen(
        backend_cmd, cwd=str(backend_dir), env=env,
        creationflags=popen_creationflags,
    )

    if not _wait_for_port(api_port, timeout=20):
        typer.echo("  backend did not become ready within 20s — aborting.", err=True)
        backend.terminate()
        return 3

    typer.echo("  backend ready. starting Vite dev server …")
    # Use `npm.cmd` explicitly on Windows so we don't have to go through the
    # shell. shell=True with quoted arg lists is fragile under cmd.exe.
    npm_exe = "npm.cmd" if os.name == "nt" else "npm"
    frontend_cmd = [npm_exe, "run", "dev", "--", "--port", str(web_port), "--strictPort"]
    frontend = subprocess.Popen(
        frontend_cmd, cwd=str(frontend_dir), env=env,
        creationflags=popen_creationflags,
    )

    studio_url = f"http://127.0.0.1:{web_port}/?worktree={project}"
    if open_browser and _wait_for_port(web_port, timeout=30):
        webbrowser.open(studio_url)

    typer.echo("")
    typer.echo(f"  open in browser: {studio_url}")
    typer.echo("  press Ctrl-C to stop.")
    typer.echo("")

    try:
        # Wait on either process — if one dies, take the other down with it.
        while True:
            if backend.poll() is not None:
                typer.echo("backend exited; stopping studio.", err=True)
                break
            if frontend.poll() is not None:
                typer.echo("studio exited; stopping backend.", err=True)
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        typer.echo("\nstopping …")
    finally:
        for proc in (frontend, backend):
            if proc.poll() is None:
                try:
                    if os.name == "nt":
                        proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                    else:
                        proc.terminate()
                except (OSError, ValueError):
                    pass
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
    return 0


def register_explore_command(app: typer.Typer) -> None:
    @app.command()
    def explore(
        project_dir: Optional[str] = typer.Option(
            None, "--project-dir", "-p",
            help="Project directory to open. Defaults to the current working directory.",
        ),
        port: int = typer.Option(
            5173, "--port",
            help="Preferred Vite dev-server port (auto-falls-back if taken).",
        ),
        no_browser: bool = typer.Option(
            False, "--no-browser",
            help="Boot the studio but don't open a browser tab.",
        ),
        init: bool = typer.Option(
            False, "--init",
            help="Generate `.uiplan/explorer.yaml` for the project and exit.",
        ),
        check: bool = typer.Option(
            False, "--check",
            help="Run the indexer once and print a summary, no UI.",
        ),
    ) -> None:
        """Open the UiPlan Studio Explorer for a UiPath project.

        With no flags, boots the studio for the current directory. Use --init
        to drop a starter config into a project, --check to validate what
        the indexer would produce.
        """
        project = _detect_project_dir(project_dir)
        if init:
            _do_init(project)
            return
        if check:
            _print_indexer_summary(project)
            return
        rc = _do_explore(project, port=port, open_browser=not no_browser)
        raise typer.Exit(rc)
