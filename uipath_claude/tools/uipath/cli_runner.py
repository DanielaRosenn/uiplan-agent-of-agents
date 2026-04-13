"""Subprocess helpers for official uipath CLI (studio package analyze/pack)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


_STUDIO_UNAVAILABLE_MARKERS = (
    "interop",
    "autopilot",
    "dependencyexception",
    "could not load file or assembly",
)


def _collect_text_fragments(value: Any) -> list[str]:
    """Recursively collect non-empty string fragments from nested payloads."""
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        fragments: list[str] = []
        for item in value:
            fragments.extend(_collect_text_fragments(item))
        return fragments
    if isinstance(value, dict):
        fragments = []
        preferred_keys = (
            "message",
            "Message",
            "error",
            "Error",
            "details",
            "Details",
            "exception",
            "Exception",
        )
        for key in preferred_keys:
            if key in value:
                fragments.extend(_collect_text_fragments(value[key]))
        if fragments:
            return fragments
        for nested_value in value.values():
            fragments.extend(_collect_text_fragments(nested_value))
        return fragments
    return []


def _extract_cli_message(payload: dict[str, Any]) -> str:
    """Extract the best available message string from CLI JSON response."""
    data = payload.get("Data")
    if isinstance(data, dict):
        for key in ("message", "Message"):
            if key in data:
                fragments = _collect_text_fragments(data[key])
                if fragments:
                    return "\n".join(fragments)
    for key in ("Message", "message"):
        if key in payload:
            fragments = _collect_text_fragments(payload[key])
            if fragments:
                return "\n".join(fragments)
    return ""


def _parse_get_errors_message(message: str) -> list[str]:
    """Parse diagnostics lines from get-errors output text."""
    normalized = message.strip()
    if not normalized:
        return []
    if "No diagnostics found" in normalized:
        return []

    lines = normalized.splitlines()
    parsed = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            parsed.append(stripped[2:].strip())
    if parsed:
        return parsed

    if normalized.startswith("Errors"):
        return [normalized]
    return [normalized]


def _studio_unavailable_error(message: str) -> str | None:
    """Return an explicit Studio-unavailable message when signature is detected."""
    lowered = message.lower()
    if not any(marker in lowered for marker in _STUDIO_UNAVAILABLE_MARKERS):
        return None
    return (
        "UiPath Studio is unavailable. File-level diagnostics could not run "
        f"(interop/autopilot/dependency exception): {message.strip()}"
    )


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
    file_path: str | Path | None = None,
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
    command = [uip_cli, "rpa", "get-errors", "--project-dir", path]
    if file_path is not None:
        command.extend(["--file-path", str(Path(file_path).resolve())])
    command.extend(["--output", "json"])
    try:
        proc = subprocess.run(
            command,
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
            "diagnostics_ran": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "errors": [f"Validation timed out after {timeout}s"],
            "raw_output": "",
            "diagnostics_ran": False,
        }
    
    output = proc.stdout or ""
    errors = []
    diagnostics_ran = True
    
    try:
        result = json.loads(output)
        message = _extract_cli_message(result) if isinstance(result, dict) else ""
        studio_unavailable = _studio_unavailable_error(message)
        if studio_unavailable:
            return {
                "success": False,
                "errors": [studio_unavailable],
                "raw_output": output,
                "diagnostics_ran": False,
            }

        if isinstance(result, dict) and result.get("Result") == "Success":
            parsed_errors = _parse_get_errors_message(message)
            if not parsed_errors:
                return {
                    "success": True,
                    "errors": [],
                    "raw_output": output,
                    "diagnostics_ran": diagnostics_ran,
                }
            return {
                "success": False,
                "errors": parsed_errors,
                "raw_output": output,
                "diagnostics_ran": diagnostics_ran,
            }
        else:
            errors.append(message or "Unknown error")
    except json.JSONDecodeError:
        if proc.returncode != 0:
            raw_error = proc.stderr or output or "Validation failed"
            studio_unavailable = _studio_unavailable_error(raw_error)
            if studio_unavailable:
                errors.append(studio_unavailable)
                diagnostics_ran = False
            else:
                errors.append(raw_error)
    
    return {
        "success": len(errors) == 0,
        "errors": errors,
        "raw_output": output,
        "diagnostics_ran": diagnostics_ran,
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
            studio_unavailable = _studio_unavailable_error(error_msg)
            if studio_unavailable:
                errors.append(studio_unavailable)
                return {
                    "success": False,
                    "errors": errors,
                    "warnings": warnings,
                    "raw_output": output,
                }
            # Check if it's a "project already open" or "missing project file" error
            if ("already opened in another Studio instance" in error_msg or
                "No project.uiproj" in error_msg or
                "webAppManifest.json" in error_msg):
                # Fall back to get-errors for standalone XAML files
                return run_uip_rpa_get_errors(project_path, timeout=timeout)
            errors.append(error_msg)
    except json.JSONDecodeError:
        if proc.returncode != 0:
            raw_error = proc.stderr or output or "Analysis failed"
            studio_unavailable = _studio_unavailable_error(raw_error)
            errors.append(studio_unavailable or raw_error)
    
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
