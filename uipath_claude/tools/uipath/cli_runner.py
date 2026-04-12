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


def run_uip_rpa_analyze(
    project_path: str | Path,
    *,
    timeout: int = 120,
) -> dict:
    """Run `uip rpa analyze --project-path <project> --output json`.
    
    This performs deeper validation than get-errors, including:
    - Package dependency resolution
    - Activity existence validation
    - Workflow analysis rules
    
    Returns dict with:
        - success: bool
        - errors: list of error strings
        - warnings: list of warning strings
        - raw_output: str
    """
    path = str(Path(project_path).resolve())
    uip_cli = _find_uip_cli()
    try:
        proc = subprocess.run(
            [uip_cli, "rpa", "analyze", "--project-path", path, "--output", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {
            "success": False,
            "errors": ["uip CLI not found. Install with: npm install -g @uipath/cli"],
            "warnings": [],
            "raw_output": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "errors": [f"Analysis timed out after {timeout}s"],
            "warnings": [],
            "raw_output": "",
        }
    
    output = proc.stdout or ""
    errors = []
    warnings = []
    
    try:
        result = json.loads(output)
        if result.get("Result") == "Success":
            # Analyze succeeded - check for issues in the data
            data = result.get("Data", {})
            issues = data.get("Issues", [])
            for issue in issues:
                severity = issue.get("Severity", "").lower()
                message = issue.get("Message", "")
                if severity == "error":
                    errors.append(message)
                elif severity in ("warning", "warn"):
                    warnings.append(message)
            return {
                "success": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "raw_output": output,
            }
        else:
            # Analyze failed
            error_msg = result.get("Message", "Unknown error")
            # Check if it's a "project already open" or "missing project file" error
            if ("already opened in another Studio instance" in error_msg or
                "No project.uiproj" in error_msg or
                "webAppManifest.json" in error_msg):
                # Fall back to get-errors for standalone XAML files
                return run_uip_rpa_get_errors(project_path, timeout=timeout)
            errors.append(error_msg)
    except json.JSONDecodeError:
        if proc.returncode != 0:
            errors.append(proc.stderr or output or "Analysis failed")
    
    return {
        "success": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
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


def run_uip_rpa_find_activities(
    query: str,
    *,
    timeout: int = 30,
) -> dict:
    """Run `uip rpa find-activities --query <query> --output json`.
    
    Searches for activities matching a query string.
    
    Returns dict with:
        - success: bool
        - activities: list of dicts with activity info
        - raw_output: str
    """
    uip_cli = _find_uip_cli()
    try:
        proc = subprocess.run(
            [uip_cli, "rpa", "find-activities", "--query", query, "--output", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {
            "success": False,
            "activities": [],
            "raw_output": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "activities": [],
            "raw_output": "",
        }
    
    output = proc.stdout or ""
    
    try:
        result = json.loads(output)
        if result.get("Result") == "Success":
            data = result.get("Data", {})
            activities = data.get("Activities", []) if isinstance(data, dict) else []
            return {
                "success": True,
                "activities": activities,
                "raw_output": output,
            }
    except json.JSONDecodeError:
        pass
    
    return {
        "success": False,
        "activities": [],
        "raw_output": output,
    }


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
