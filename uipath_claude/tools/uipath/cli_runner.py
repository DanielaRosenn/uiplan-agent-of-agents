"""Subprocess helpers for official uipath CLI (studio package analyze/pack)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _find_uip_cli() -> str:
    """Find the uip CLI executable path."""
    npm_global = os.environ.get("APPDATA", "")
    if npm_global:
        uip_cmd = Path(npm_global) / "npm" / "uip.cmd"
        if uip_cmd.exists():
            return str(uip_cmd)
    return "uip"


def run_uip_rpa_get_errors(
    project_path: str | Path,
    *,
    timeout: int = 120,
) -> dict:
    """Run `uip rpa get-errors --project-dir <project> --output json`.
    
    Returns dict with:
        - success: bool
        - errors: list of error strings
        - raw_output: str
    """
    path = str(Path(project_path).resolve())
    uip_cli = _find_uip_cli()
    try:
        proc = subprocess.run(
            [uip_cli, "rpa", "get-errors", "--project-dir", path, "--output", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {
            "success": False,
            "errors": ["uip CLI not found. Install with: npm install -g @uipath/cli"],
            "raw_output": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "errors": [f"Validation timed out after {timeout}s"],
            "raw_output": "",
        }
    
    output = proc.stdout or ""
    errors = []
    
    try:
        result = json.loads(output)
        if result.get("Result") == "Success":
            data = result.get("Data", {})
            message = data.get("message", "")
            if "No diagnostics found" in message:
                return {"success": True, "errors": [], "raw_output": output}
            if message.startswith("Errors"):
                error_lines = message.split("\n")
                for line in error_lines[1:]:
                    line = line.strip()
                    if line.startswith("- "):
                        errors.append(line[2:])
                return {"success": False, "errors": errors, "raw_output": output}
        else:
            errors.append(result.get("Message", "Unknown error"))
    except json.JSONDecodeError:
        if proc.returncode != 0:
            errors.append(proc.stderr or output or "Validation failed")
    
    return {
        "success": len(errors) == 0,
        "errors": errors,
        "raw_output": output,
    }


def run_studio_package_analyze(
    project_path: str | Path,
    *,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    """Run `uipath studio package analyze <project>` (legacy)."""
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
