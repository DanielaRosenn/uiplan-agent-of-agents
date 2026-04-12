"""Subprocess helpers for official uipath CLI (studio package analyze/pack)."""
from __future__ import annotations

import subprocess
from pathlib import Path


def run_studio_package_analyze(
    project_path: str | Path,
    *,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    """Run `uipath studio package analyze <project>`."""
    path = str(Path(project_path).resolve())
    return subprocess.run(
        ["uipath", "studio", "package", "analyze", path],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_studio_package_pack(
    project_path: str | Path,
    *,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    """Run `uipath studio package pack <project>`."""
    path = str(Path(project_path).resolve())
    return subprocess.run(
        ["uipath", "studio", "package", "pack", path],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def format_cli_result(
    label: str,
    proc: subprocess.CompletedProcess[str],
) -> str:
    """Human-readable single-command result."""
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    body = "\n".join(p for p in (out, err) if p)
    status = "OK" if proc.returncode == 0 else f"exit {proc.returncode}"
    return f"{label} ({status}):\n{body or '(no output)'}"
