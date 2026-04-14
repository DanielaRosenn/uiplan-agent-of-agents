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


def _parse_first_json_payload(text: str) -> dict | None:
    """Parse the first JSON object found in tool output."""
    start = text.find("{")
    if start < 0:
        return None
    try:
        payload, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def run_uip_rpa_get_errors(
    project_path: str | Path,
    *,
    file_path: str | None = None,
    timeout: int = 120,
    use_studio: bool = True,
) -> dict:
    """Run `uip rpa get-errors --project-dir <project> --output json`.
    
    Args:
        project_path: Path to the UiPath project directory
        file_path: Optional specific file to validate (relative to project)
        timeout: Command timeout in seconds
    
    Returns dict with:
        - success: bool
        - errors: list of error strings
        - warnings: list of warning strings
        - raw_output: str
        - studio_required: bool (True if validation requires Studio)
    """
    path = str(Path(project_path).resolve())
    uip_cli = _find_uip_cli()
    
    cmd = [uip_cli, "rpa", "get-errors", "--project-dir", path, "--output", "json"]
    if file_path:
        cmd.extend(["--file-path", file_path])
    if use_studio:
        cmd.append("--use-studio")
    
    try:
        proc = subprocess.run(
            cmd,
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
            "studio_required": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "errors": [f"Validation timed out after {timeout}s"],
            "warnings": [],
            "raw_output": "",
            "studio_required": False,
        }
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    errors: list[str] = []
    warnings: list[str] = []
    
    # Check if Studio interaction is blocked (not running / interop failures)
    studio_required = (
        "IInteropProjectService" in output or
        "IAutopilotValidationService" in output or
        "DependencyResolutionException" in output or
        "Studio" in output and "not" in output.lower()
    )
    
    try:
        result = _parse_first_json_payload(output)
        if result is None:
            raise json.JSONDecodeError("No JSON payload", output, 0)
        if result.get("Result") == "Success":
            data = result.get("Data", {})
            message = data.get("message", "")
            if "No diagnostics found" in message:
                return {
                    "success": True, 
                    "errors": [], 
                    "warnings": [],
                    "raw_output": output,
                    "studio_required": False,
                }
            # Parse errors/warnings from text payload
            if message:
                for line in message.split("\n"):
                    line = line.strip()
                    if line.startswith("- "):
                        item = line[2:]
                        if "warning" in item.lower():
                            warnings.append(item)
                        else:
                            errors.append(item)
                return {
                    "success": len(errors) == 0, 
                    "errors": errors, 
                    "warnings": warnings,
                    "raw_output": output,
                    "studio_required": False,
                }
        else:
            error_msg = result.get("Message", "Unknown error")
            # Sometimes Message is a JSON string with "errorMessage"
            if isinstance(error_msg, str):
                try:
                    nested = json.loads(error_msg)
                    parsed = nested.get("errorMessage")
                    if isinstance(parsed, str) and parsed.strip():
                        error_msg = parsed
                except Exception:
                    pass
            errors.append(str(error_msg))
    except json.JSONDecodeError:
        if proc.returncode != 0:
            errors.append(proc.stderr or output or "Validation failed")
    
    return {
        "success": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "raw_output": output,
        "studio_required": studio_required,
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
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    errors = []
    warnings = []
    
    try:
        result = _parse_first_json_payload(output)
        if result is None:
            raise json.JSONDecodeError("No JSON payload", output, 0)
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
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    
    try:
        result = _parse_first_json_payload(output)
        if result is None:
            raise json.JSONDecodeError("No JSON payload", output, 0)
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


def run_uip_rpa_get_default_activity_xaml(
    activity_class_name: str,
    *,
    project_dir: str | Path | None = None,
    timeout: int = 60,
) -> dict:
    """Run `uip rpa get-default-activity-xaml --activity-class-name <class> --output json`.
    
    Gets the correct XAML for an activity as it would appear when dropped into Studio.
    This is the authoritative source for activity XAML structure.
    
    Args:
        activity_class_name: Fully qualified class name (e.g., 'UiPath.Mail.Outlook.Activities.GetOutlookMailMessages')
        project_dir: Optional project directory for context
        timeout: Command timeout in seconds
        
    Returns dict with:
        - success: bool
        - xaml: str (the activity XAML)
        - namespaces: list of required xmlns declarations
        - raw_output: str
    """
    uip_cli = _find_uip_cli()
    cmd = [uip_cli, "rpa", "get-default-activity-xaml", 
           "--activity-class-name", activity_class_name, 
           "--output", "json"]
    if project_dir:
        cmd.extend(["--project-dir", str(Path(project_dir).resolve())])
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {
            "success": False,
            "xaml": "",
            "namespaces": [],
            "raw_output": "",
            "error": "uip CLI not found",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "xaml": "",
            "namespaces": [],
            "raw_output": "",
            "error": f"Command timed out after {timeout}s",
        }
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    
    try:
        result = _parse_first_json_payload(output)
        if result is None:
            raise json.JSONDecodeError("No JSON payload", output, 0)
        if result.get("Result") == "Success":
            data = result.get("Data", {})
            return {
                "success": True,
                "xaml": data.get("Xaml", ""),
                "namespaces": data.get("Namespaces", []),
                "raw_output": output,
            }
        else:
            return {
                "success": False,
                "xaml": "",
                "namespaces": [],
                "raw_output": output,
                "error": result.get("Message", "Unknown error"),
            }
    except json.JSONDecodeError:
        return {
            "success": False,
            "xaml": "",
            "namespaces": [],
            "raw_output": output,
            "error": "Failed to parse response",
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
