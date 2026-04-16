"""Tools for agentic skill execution.

These tools are bound to the LLM during skill execution, allowing it to
read/write files, run CLI commands, validate workflows, and install packages.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread
from typing import Any, Optional, Tuple

from langchain_core.tools import tool

from uipath_claude.tools._result import ToolOutcome
from uipath_claude.tools.library_tools import get_library_tools
from uipath_claude.tools.uipath.cli_runner import (
    _find_uip_cli,
    _parse_first_json_payload,
    run_uip_rpa_get_errors,
)


# Maximum file size to read (50KB)
MAX_FILE_SIZE = 50 * 1024


def _get_output_root() -> Path:
    """Get the output root directory for generated files."""
    default = Path.cwd() / "generated" / "chat"
    return Path(os.environ.get("UIPATH_CHAT_OUTPUT_DIR", str(default)))


def _resolve_project_path(project_dir: str) -> Path:
    """Resolve project directory, preferring CWD if it has project.json.
    
    This allows tools to work both:
    1. In test fixtures where CWD has project.json
    2. In normal operation where files go to generated/chat/<session_id>/
    
    Args:
        project_dir: Relative or absolute path to project directory
        
    Returns:
        Resolved Path to the project directory
    """
    path = Path(project_dir)
    if path.is_absolute():
        return path
    
    # Check if CWD has project.json (test fixture or real project scenario)
    cwd_path = Path.cwd() / project_dir
    if (cwd_path / "project.json").exists():
        return cwd_path
    
    # Also check if CWD itself is a project (project_dir is ".")
    if project_dir in (".", "") and (Path.cwd() / "project.json").exists():
        return Path.cwd()
    
    # Fall back to generated output directory
    output_root = _get_output_root()
    session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
    if session_id:
        return output_root / session_id / project_dir
    return output_root / project_dir


def _resolve_file_path(file_path: str) -> Path:
    """Resolve file path, preferring CWD if it's in a project directory.
    
    Args:
        file_path: Relative or absolute path to a file
        
    Returns:
        Resolved Path to the file
    """
    path = Path(file_path)
    if path.is_absolute():
        return path
    
    # Check if file exists in CWD (test fixture or real project scenario)
    cwd_path = Path.cwd() / file_path
    if cwd_path.exists():
        return cwd_path
    
    # Check if CWD has project.json (we're in a project directory)
    if (Path.cwd() / "project.json").exists():
        return cwd_path
    
    # Fall back to generated output directory
    output_root = _get_output_root()
    session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
    if session_id:
        return output_root / session_id / file_path
    return output_root / file_path


def _resolve_safe_path(base: Path, relative: str) -> Path | None:
    """Resolve a path safely, preventing directory traversal."""
    relative = relative.strip().replace("\\", "/")
    if not relative or relative.startswith("/"):
        return None
    if Path(relative).is_absolute():
        return None
    parts = Path(relative).parts
    if ".." in parts:
        return None
    dest = (base / relative).resolve()
    try:
        dest.relative_to(base.resolve())
    except ValueError:
        return None
    return dest


def _tool(ok: bool, message: str) -> str:
    return ToolOutcome(ok=ok, message=message).to_text()


@tool
def read_file(file_path: str) -> str:
    """Read contents of a file.
    
    Use this to read project.json, existing XAML files, .cs files, etc.
    Files larger than 50KB will be truncated.
    
    Args:
        file_path: Path to the file (absolute or relative to output root)
    
    Returns:
        File contents as string, or error message if file not found
    """
    path = _resolve_file_path(file_path)
    
    if not path.exists():
        return _tool(False, f"Error: File not found: {file_path}")
    
    try:
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            content = path.read_text(encoding="utf-8")[:MAX_FILE_SIZE]
            return _tool(
                True,
                f"{content}\n\n[TRUNCATED - file is {size} bytes, showing first {MAX_FILE_SIZE}]",
            )
        return _tool(True, path.read_text(encoding="utf-8"))
    except Exception as e:
        return _tool(False, f"Error reading file: {e}")


def _validate_xml_structure(content: str) -> str | None:
    """Validate basic XML structure. Returns error message or None if valid."""
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(content)
        return None
    except ET.ParseError as e:
        return f"XML parsing error: {e}"


def _fix_xaml_content(content: str) -> str:
    """Fix common XAML issues from LLM output."""
    import re
    
    # Fix 1: Remove wrapper tags like <xaml>...</xaml>
    content = re.sub(r'^\s*<xaml>\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\s*</xaml>\s*$', '', content, flags=re.IGNORECASE)
    
    # Fix 2: Remove CDATA wrappers
    content = re.sub(r'^\s*<!\[CDATA\[\s*', '', content)
    content = re.sub(r'\s*\]\]>\s*$', '', content)
    
    # Fix 3: Fix escaped XML where < > are escaped inside XML
    if "&lt;" in content and content.strip().startswith("<"):
        content = content.replace("&lt;", "<").replace("&gt;", ">")
    
    return content.strip()


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file.
    
    Use this to create or update XAML workflows, .cs files, etc.
    Parent directories will be created if they don't exist.
    
    IMPORTANT: For XAML files, the content must be valid XML.
    Do NOT escape < and > characters - use them directly.
    
    Args:
        file_path: Relative path for the file (relative to session output dir)
        content: File content to write
    
    Returns:
        Success message with absolute path, or error message
    """
    # Use CWD if it's a project directory (has project.json)
    if (Path.cwd() / "project.json").exists():
        base = Path.cwd()
    else:
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            base = output_root / session_id
        else:
            base = output_root
    
    dest = _resolve_safe_path(base, file_path)
    if dest is None:
        return _tool(False, f"Error: Invalid file path: {file_path}")
    
    # For XAML files, validate XML structure and fix common issues
    if file_path.lower().endswith(".xaml"):
        # Try to fix common XAML issues
        fixed_content = _fix_xaml_content(content)
        
        # Validate XML structure
        xml_error = _validate_xml_structure(fixed_content)
        if xml_error:
            return _tool(
                False,
                f"Error: Invalid XAML - {xml_error}. Make sure all XML tags use < and > directly, not &lt; and &gt;.",
            )
        
        content = fixed_content
    
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return _tool(True, f"Successfully wrote {len(content)} bytes to {dest}")
    except Exception as e:
        return _tool(False, f"Error writing file: {e}")


@tool
def list_directory(dir_path: str = ".", pattern: str = "*") -> str:
    """List files in a directory matching a glob pattern.
    
    Use this to discover existing files in the project.
    
    Args:
        dir_path: Directory path (relative to session output dir, or absolute)
        pattern: Glob pattern like *.xaml, *.cs, **/*.json
    
    Returns:
        List of matching file paths, one per line
    """
    path = _resolve_project_path(dir_path)
    
    if not path.exists():
        return _tool(False, f"Error: Directory not found: {dir_path}")
    
    if not path.is_dir():
        return _tool(False, f"Error: Not a directory: {dir_path}")
    
    try:
        matches = list(path.glob(pattern))
        if not matches:
            return _tool(True, f"No files matching '{pattern}' in {dir_path}")
        
        result = []
        for m in sorted(matches)[:100]:  # Limit to 100 results
            if m.is_file():
                try:
                    rel = m.relative_to(path)
                    result.append(str(rel))
                except ValueError:
                    result.append(str(m))
        
        body = "\n".join(result) if result else f"No files matching '{pattern}'"
        return _tool(True, body)
    except Exception as e:
        return _tool(False, f"Error listing directory: {e}")


@tool
def read_project_json(project_dir: str = ".") -> str:
    """Read and parse project.json, returning key information.
    
    Use this to check current dependencies, entry points, and project settings
    before adding new packages or workflows.
    
    Args:
        project_dir: Path to the UiPath project directory
    
    Returns:
        JSON string with project name, dependencies, entry points, and settings
    """
    path = _resolve_project_path(project_dir)
    
    project_json = path / "project.json"
    if not project_json.exists():
        return _tool(False, f"Error: project.json not found in {project_dir}")
    
    try:
        data = json.loads(project_json.read_text(encoding="utf-8"))
        summary = {
            "name": data.get("name", "unknown"),
            "dependencies": data.get("dependencies", {}),
            "entryPoints": [
                ep.get("filePath") for ep in data.get("entryPoints", [])
            ],
            "expressionLanguage": data.get("expressionLanguage", "VisualBasic"),
            "targetFramework": data.get("targetFramework", "Windows"),
            "schemaVersion": data.get("schemaVersion", "unknown"),
        }
        return _tool(True, json.dumps(summary, indent=2))
    except Exception as e:
        return _tool(False, f"Error reading project.json: {e}")


@tool
def install_package(project_dir: str, package_id: str, version: str | None = None) -> str:
    """Install a NuGet package into the UiPath project.
    
    This runs: uip rpa install-or-update-packages --use-studio
    
    IMPORTANT: Always check current dependencies with read_project_json first
    to avoid installing packages that are already present.
    
    Args:
        project_dir: Path to the UiPath project directory
        package_id: NuGet package ID (e.g., "UiPath.Mail.Activities")
        version: Optional version constraint (e.g., "2.5.10")
    
    Returns:
        Success or error message
    """
    path = _resolve_project_path(project_dir)
    
    if not (path / "project.json").exists():
        return _tool(False, f"Error: No project.json found in {project_dir}")
    
    uip_cli = _find_uip_cli()
    
    package_spec: dict[str, Any] = {"id": package_id}
    if version:
        package_spec["version"] = version
    
    packages_json = json.dumps([package_spec])
    
    cmd = [
        uip_cli, "rpa", "install-or-update-packages",
        "--packages", packages_json,
        "--project-dir", str(path.resolve()),
        "--output", "json",
    ]
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        return _tool(False, "Error: uip CLI not found. Install with: npm install -g @uipath/cli")
    except subprocess.TimeoutExpired:
        return _tool(False, "Error: Package installation timed out after 120s")
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    
    if proc.returncode == 0:
        return _tool(
            True,
            f"Successfully installed {package_id}" + (f" version {version}" if version else ""),
        )
    
    result = _parse_first_json_payload(output)
    if result and result.get("Message"):
        return _tool(False, f"Error installing package: {result['Message']}")
    
    return _tool(False, f"Error installing package: {output[:500]}")


@tool
def validate_file(project_dir: str, file_path: str | None = None) -> str:
    """Run uip rpa get-errors to validate a workflow file.
    
    This validates XAML/CS files against UiPath Studio.
    ALWAYS run this after creating or modifying workflow files.
    
    Args:
        project_dir: Path to the UiPath project directory
        file_path: Optional specific file to validate (relative to project)
    
    Returns:
        Validation result with errors and warnings
    """
    path = _resolve_project_path(project_dir)
    
    result = run_uip_rpa_get_errors(
        str(path.resolve()),
        file_path=file_path,
        use_studio=False,
    )
    
    if result["success"]:
        msg = "Validation passed: 0 errors"
        if result["warnings"]:
            msg += f", {len(result['warnings'])} warning(s)"
            for w in result["warnings"][:5]:
                msg += f"\n  - {w}"
        return _tool(True, msg)
    
    msg = f"Validation failed: {len(result['errors'])} error(s)"
    for e in result["errors"][:10]:
        msg += f"\n  - {e}"
    if result["warnings"]:
        msg += f"\n{len(result['warnings'])} warning(s):"
        for w in result["warnings"][:5]:
            msg += f"\n  - {w}"
    
    if result.get("studio_required"):
        msg += "\n\nNote: Full validation requires UiPath Studio to be running."
    
    return _tool(False, msg)


@tool
def run_uip_command(
    command: str,
    command_args: list[str],
    project_dir: str | None = None,
) -> str:
    """Run any uip CLI command.
    
    Use this for commands not covered by other tools, such as:
    - uip rpa find-activities --query "GetOutlook"
    - uip rpa get-default-activity-xaml --activity-class-name "..."
    - uip rpa list-instances
    - uip rpa create-project --name "..." --location "..."
    
    Args:
        command: The uip subcommand (e.g., "rpa", "is")
        command_args: Arguments after the subcommand (e.g. ``["find-activities", "--query", "X"]``)
        project_dir: Optional project directory for context
    
    Returns:
        Command output or error message
    """
    uip_cli = _find_uip_cli()

    # Flags not supported on all uip CLI builds (model sometimes still emits them)
    _strip_flags = frozenset({"--use-studio"})
    stripped: list[str] = []
    filtered_args: list[str] = []
    for arg in command_args:
        if arg in _strip_flags:
            stripped.append(arg)
        else:
            filtered_args.append(arg)
    command_args = filtered_args

    cmd = [uip_cli, command] + command_args

    # Set working directory if project_dir provided
    cwd = None
    if project_dir:
        path = _resolve_project_path(project_dir)
        if path.exists():
            cwd = str(path.resolve())
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd,
            check=False,
        )
    except FileNotFoundError:
        return _tool(False, "Error: uip CLI not found. Install with: npm install -g @uipath/cli")
    except subprocess.TimeoutExpired:
        return _tool(False, "Error: Command timed out after 60s")
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)

    note = ""
    if stripped:
        note = (
            "Note: removed unsupported uip flag(s): "
            + ", ".join(stripped)
            + "\n\n"
        )

    # Try to extract JSON result if present
    result = _parse_first_json_payload(output)
    if result:
        if result.get("Result") == "Success":
            data = result.get("Data", result)
            body = json.dumps(data, indent=2)[:5000]
            return _tool(True, note + body if note else body)
        elif result.get("Message"):
            return _tool(False, note + f"Error: {result['Message']}")

    # Return raw output (truncated)
    tail = output[:5000] if output else "(no output)"
    ok = proc.returncode == 0
    return _tool(ok, note + tail if note else tail)


@tool
def find_activity_info(query: str, project_dir: str | None = None) -> str:
    """Search for UiPath activity documentation.
    
    Checks in order:
    1. Bundled activity-docs in skill references (most detailed)
    2. .local/docs/packages/ (project-specific)
    3. uip rpa find-activities (live CLI query)
    
    ALWAYS use this before using an unfamiliar activity to understand:
    - Correct property names (e.g., Messages vs Result)
    - Required package
    - XAML syntax examples
    
    Args:
        query: Activity name to search for (e.g., "GetOutlookMailMessages")
        project_dir: Optional project directory for context
    
    Returns:
        Activity documentation including package, properties, XAML example
    """
    import re
    
    # First, check bundled activity docs (most detailed)
    skills_root = Path(__file__).resolve().parent.parent.parent / "skills"
    activity_docs = skills_root / "skills" / "uipath-rpa" / "references" / "activity-docs"
    
    if activity_docs.is_dir():
        # Search for matching markdown file
        query_lower = query.lower().replace(" ", "")
        for md_file in activity_docs.rglob("*.md"):
            if query_lower in md_file.stem.lower().replace(" ", ""):
                content = md_file.read_text(encoding="utf-8")
                # Extract package from path
                package = md_file.parent.name if md_file.parent != activity_docs else "unknown"
                return _tool(
                    True,
                    f"Activity: {md_file.stem}\nPackage: {package}\nSource: bundled_docs\n\n{content[:4000]}",
                )
    
    # Fallback to ActivityDiscovery
    from uipath_claude.activities.discovery import ActivityDiscovery
    
    # Determine project path
    if project_dir:
        path = _resolve_project_path(project_dir)
    else:
        path = _resolve_project_path(".")
    
    discovery = ActivityDiscovery(skills_root)
    info = discovery.find_activity(query, path)
    
    if info is None:
        return _tool(
            False,
            f"No documentation found for activity: {query}. Try searching UiPath docs at https://docs.uipath.com/activities",
        )
    
    result = [
        f"Activity: {info.name}",
        f"Full name: {info.full_name}",
        f"Package: {info.package_id}" if info.package_id else "Package: unknown",
        f"Source: {info.source}",
        "",
        "Description:",
        info.description[:2000] if info.description else "(no description)",
    ]
    
    if info.example_xaml:
        result.extend(["", "Example XAML:", info.example_xaml[:2000]])
    
    return _tool(True, "\n".join(result))


@tool
def validate_and_fix_loop(
    project_dir: str,
    file_path: str,
    max_attempts: int = 5,
) -> str:
    """Run validation loop per uipath-rpa skill rules.
    
    This tool:
    1. Runs uip rpa get-errors on the file
    2. Reports errors found
    3. Does NOT automatically fix - returns errors for the LLM to fix
    
    The LLM should:
    1. Call this to get errors
    2. Fix one error at a time with write_file
    3. Call this again to verify
    4. Repeat until 0 errors or max_attempts
    
    Args:
        project_dir: Path to the UiPath project directory
        file_path: Relative path to the file to validate
        max_attempts: Maximum validation attempts (default 5)
    
    Returns:
        Validation status and list of errors to fix
    """
    path = _resolve_project_path(project_dir)
    
    result = run_uip_rpa_get_errors(
        str(path.resolve()),
        file_path=file_path,
        use_studio=False,
    )
    
    if result["success"]:
        return _tool(True, f"VALIDATION PASSED: {file_path} has 0 errors")
    
    errors = result["errors"]
    warnings = result["warnings"]
    
    msg = f"VALIDATION FAILED: {len(errors)} error(s) in {file_path}\n\n"
    msg += "ERRORS (fix one at a time):\n"
    for i, err in enumerate(errors[:max_attempts], 1):
        msg += f"  {i}. {err}\n"
    
    if warnings:
        msg += f"\nWARNINGS ({len(warnings)}):\n"
        for w in warnings[:5]:
            msg += f"  - {w}\n"
    
    msg += "\nINSTRUCTIONS: Fix the FIRST error, then call validate_and_fix_loop again."
    
    return _tool(False, msg)


@tool
def debug_workflow(project_dir: str, file_path: str) -> str:
    """Run a workflow in debug mode.
    
    This runs: uip rpa run-file --file-path <file> --command StartDebugging
    
    WARNING: This will actually execute the workflow. Only use for testing
    workflows that don't have side effects, or when the user explicitly
    requests it.
    
    Args:
        project_dir: Path to the UiPath project directory
        file_path: Relative path to the workflow file
    
    Returns:
        Execution output or error message
    """
    path = _resolve_project_path(project_dir)
    
    uip_cli = _find_uip_cli()
    
    cmd = [
        uip_cli, "rpa", "run-file",
        "--file-path", file_path,
        "--project-dir", str(path.resolve()),
        "--command", "StartDebugging",
        "--output", "json",
        "--use-studio",
    ]
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for execution
            check=False,
        )
    except FileNotFoundError:
        return _tool(False, "Error: uip CLI not found. Install with: npm install -g @uipath/cli")
    except subprocess.TimeoutExpired:
        return _tool(False, "Error: Workflow execution timed out after 5 minutes")
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    
    if proc.returncode == 0:
        return _tool(True, f"Workflow executed successfully.\n\nOutput:\n{output[:2000]}")
    
    return _tool(
        False,
        f"Workflow execution failed (exit code {proc.returncode}).\n\nOutput:\n{output[:2000]}",
    )


def _analyze_error_message(error_msg: str, activity_name: str = "") -> str:
    """Convert technical error message to actionable fix suggestion.
    
    Args:
        error_msg: The error message from runtime execution
        activity_name: Name of the activity that failed (if known)
    
    Returns:
        Actionable suggestion for fixing the error
    """
    error_lower = error_msg.lower()
    
    if "property" in error_lower and "does not exist" in error_lower:
        fix = f"The activity '{activity_name}' doesn't have this property."
        fix += " Use find_activity_info to check available properties and outputs."
        return fix
    
    elif "object reference not set" in error_lower or "null reference" in error_lower:
        fix = f"Variable in '{activity_name}' is null or not initialized."
        fix += " Check that previous activities set this variable correctly."
        return fix
    
    elif "cannot convert" in error_lower or "type mismatch" in error_lower:
        fix = f"Type mismatch in '{activity_name}'."
        fix += " Check that variable types match the activity's expected input/output types."
        return fix
    
    elif "missing" in error_lower and "argument" in error_lower:
        fix = f"Activity '{activity_name}' is missing a required argument."
        fix += " Use find_activity_info to check required properties."
        return fix
    
    elif "timeout" in error_lower:
        return "Activity timed out. Consider increasing timeout or checking if the operation is stuck."
    
    else:
        return error_msg


def _parse_runtime_response(response_text: str, verbose: bool = False) -> dict:
    """Parse JSON response from uip rpa run-file command.
    
    Args:
        response_text: Raw stdout from CLI command
        verbose: Whether to include all log entries
    
    Returns:
        Dictionary with parsed execution results
    """
    try:
        response = json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Failed to parse CLI response as JSON",
            "raw_output": response_text[:500]
        }
    
    is_successful = response.get("IsSuccessful", False)
    error_message = response.get("ErrorMessage", "")
    data = response.get("Data", {})
    
    # Handle case where Data is a string (error message) instead of dict
    if isinstance(data, str):
        return {
            "success": False,
            "error_message": data,
            "execution_state": "Error",
            "errors": [data],
            "log_entries": [],
            "has_more_logs": False
        }
    
    errors = data.get("Errors", []) if isinstance(data, dict) else []
    log_entries = data.get("LogEntries", []) if isinstance(data, dict) else []
    output_data = data.get("Output", {}) if isinstance(data, dict) else {}
    execution_state = output_data.get("State", "Unknown") if isinstance(output_data, dict) else "Unknown"
    
    # Filter log entries to only errors/critical unless verbose
    if not verbose:
        log_entries = [
            entry for entry in log_entries
            if entry.get("Severity") in ["Error", "Critical", "Fatal"]
        ]
    
    # Limit to first 5 error entries for token efficiency
    if len(log_entries) > 5 and not verbose:
        log_entries = log_entries[:5]
    
    original_log_count = len(data.get("LogEntries", [])) if isinstance(data, dict) else 0
    return {
        "success": is_successful and execution_state == "Completed",
        "error_message": error_message,
        "execution_state": execution_state,
        "errors": errors,
        "log_entries": log_entries,
        "has_more_logs": original_log_count > len(log_entries)
    }


def _format_runtime_result(parsed: dict, verbose: bool = False) -> str:
    """Format runtime execution results for agent consumption.
    
    Args:
        parsed: Parsed response from _parse_runtime_response
        verbose: Whether to include verbose output
    
    Returns:
        Formatted string with execution results
    """
    if parsed["success"]:
        output = "RUNTIME EXECUTION: SUCCESS\n\n"
        output += "Workflow executed successfully with no runtime errors.\n"
        
        if parsed.get("log_entries"):
            output += "\nKey log messages:\n"
            for entry in parsed["log_entries"][:3]:
                msg = entry.get("Message", "")
                output += f"  - {msg}\n"
        
        return output
    
    # Failure case
    output = "RUNTIME EXECUTION: FAILED\n\n"
    
    # Add error message if present
    if parsed.get("error_message"):
        output += f"Error: {parsed['error_message']}\n\n"
    
    # Process log entries to extract actionable info
    if parsed.get("log_entries"):
        output += "Runtime errors detected:\n\n"
        
        for entry in parsed["log_entries"]:
            severity = entry.get("Severity", "Error")
            message = entry.get("Message", "")
            activity_name = entry.get("ActivityName", "Unknown")
            exception = entry.get("ExceptionMessage", "")
            
            output += f"[{severity}] {message}\n"
            if activity_name and activity_name != "Unknown":
                output += f"Activity: {activity_name}\n"
            
            # Add actionable fix suggestion
            # Use both message and exception for analysis
            error_text = f"{message} {exception}" if exception else message
            fix_suggestion = _analyze_error_message(error_text, activity_name)
            # Always add fix if we have one (even if it's the same as error text)
            if fix_suggestion and fix_suggestion.strip():
                output += f"Fix: {fix_suggestion}\n"
            
            output += "\n"
    
    # Add validation errors if present
    if parsed.get("errors"):
        output += "Validation errors:\n"
        for error in parsed["errors"][:3]:
            output += f"  - {error}\n"
        output += "\n"
    
    # Execution state
    state = parsed.get("execution_state", "Unknown")
    output += f"Execution state: {state}\n"
    
    if parsed.get("has_more_logs") and not verbose:
        output += "\n(More log entries available - use verbose=True to see all)\n"
    
    return output


_MAX_UIP_STREAM_LINES = 5000


def _run_uip_with_optional_stream(
    cmd: list[str],
    timeout_seconds: int,
    stream_cli: bool,
) -> tuple[str, str, int]:
    """Run ``uip`` with pipes; optionally print each line to stderr while running.

    Returns ``(stdout, stderr, returncode)``. ``returncode`` is ``-1`` if the
    process was killed due to timeout. Raises ``FileNotFoundError`` if the
    executable is missing.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    out_parts: list[str] = []
    err_parts: list[str] = []
    stream_count = [0]

    def pump(pipe, parts: list[str], label: str) -> None:
        try:
            for line in iter(pipe.readline, ""):
                parts.append(line)
                if stream_cli and stream_count[0] < _MAX_UIP_STREAM_LINES:
                    stream_count[0] += 1
                    print(f"[uip {label}] {line.rstrip()}", file=sys.stderr, flush=True)
        finally:
            pipe.close()

    t_out = Thread(target=pump, args=(proc.stdout, out_parts, "stdout"), daemon=True)
    t_err = Thread(target=pump, args=(proc.stderr, err_parts, "stderr"), daemon=True)
    t_out.start()
    t_err.start()

    deadline = time.monotonic() + timeout_seconds
    while True:
        if proc.poll() is not None:
            break
        if time.monotonic() > deadline:
            proc.kill()
            t_out.join(timeout=5)
            t_err.join(timeout=5)
            return "".join(out_parts), "".join(err_parts), -1
        time.sleep(0.05)

    rc = proc.wait()
    t_out.join(timeout=60)
    t_err.join(timeout=60)
    return "".join(out_parts), "".join(err_parts), rc


@tool
def run_workflow(
    project_dir: str,
    file_path: str,
    input_arguments: str | None = None,
    timeout_seconds: int = 60,
    verbose: bool = False
) -> str:
    """Execute a workflow to verify it works at runtime.
    
    Use this AFTER static validation passes (validate_file returns 0 errors)
    to ensure the workflow actually works when run. This catches runtime issues
    that static validation cannot detect:
    
    - Wrong activity output properties (e.g., using .Result instead of .Messages)
    - Missing or incorrect variable assignments
    - Type mismatches at runtime
    - Logic errors that validation can't detect
    - Null reference exceptions
    - API or connection failures
    
    The tool runs: uip rpa run-file --command StartExecution

    Set environment variable ``UIPATH_STREAM_UIP_CLI=1`` to stream CLI stdout/stderr
    lines to stderr while the process runs (useful for long runs; JSON may be one line).

    IMPORTANT: Only use this on workflows that are safe to execute (no
    destructive operations, no production systems). This actually runs the code.
    
    Args:
        project_dir: Path to the UiPath project directory (e.g., "." or "MyProject")
        file_path: Workflow file to execute (e.g., "Main.xaml")
        input_arguments: Optional JSON string with input arguments 
                        Example: '{"orderId": "12345", "customerEmail": "test@example.com"}'
        timeout_seconds: Maximum execution time (default: 60 seconds)
        verbose: Return full logs (default: False, only shows errors)
    
    Returns:
        Execution results with:
        - Success/failure status
        - Runtime errors and exceptions
        - Relevant log messages
        - Variable values at point of failure (if any)
        
    Examples:
        >>> run_workflow(".", "Main.xaml")
        >>> run_workflow("MyProject", "Main.xaml", input_arguments='{"email":"test@example.com"}')
    """
    # 1. RESOLVE PATHS
    path = _resolve_project_path(project_dir)
    
    # Check if file exists
    workflow_file = path / file_path
    if not workflow_file.exists():
        return _tool(False, f"Error: Workflow file not found: {workflow_file}")
    
    # 2. BUILD COMMAND
    uip_cli = _find_uip_cli()
    
    cmd = [
        uip_cli, "rpa", "run-file",
        "--file-path", file_path,
        "--project-dir", str(path.resolve()),
        "--command", "StartExecution",
        "--output", "json",
    ]
    
    # Add input arguments if provided
    if input_arguments:
        cmd.extend(["--input-arguments", input_arguments])

    stream_cli = os.environ.get("UIPATH_STREAM_UIP_CLI", "").lower() in (
        "1",
        "true",
        "yes",
    )

    # 3. EXECUTE WITH TIMEOUT
    try:
        if stream_cli:
            stdout, stderr, rc = _run_uip_with_optional_stream(
                cmd, timeout_seconds, stream_cli=True
            )
            if rc == -1:
                return _tool(
                    False,
                    f"Error: Workflow execution timed out after {timeout_seconds} seconds. "
                    "The workflow may be stuck or taking too long.",
                )
            output_text = stdout if stdout else stderr
        else:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            output_text = proc.stdout if proc.stdout else proc.stderr
    except FileNotFoundError:
        return _tool(False, "Error: uip CLI not found. Install with: npm install -g @uipath/cli")
    except subprocess.TimeoutExpired:
        return _tool(
            False,
            f"Error: Workflow execution timed out after {timeout_seconds} seconds. The workflow may be stuck or taking too long.",
        )

    # 4. PARSE JSON RESPONSE
    
    if not output_text:
        return _tool(False, "Error: No output from CLI command. The workflow may not have executed.")
    
    parsed = _parse_runtime_response(output_text, verbose)
    
    # 5. FORMAT RESPONSE
    result = _format_runtime_result(parsed, verbose)
    
    # 6. TOKEN EFFICIENCY - Truncate if too long
    if len(result) > 2000 and not verbose:
        result = result[:2000] + "\n\n... (TRUNCATED - use verbose=True for full output)"
    
    return _tool(bool(parsed.get("success")), result)


@tool
def ensure_project_structure(project_dir: str = ".") -> str:
    """Ensure the project has required structure (project.json, etc).
    
    Creates a minimal project.json if missing. Use this before writing
    workflow files to ensure the project structure exists.
    
    Args:
        project_dir: Path to the project directory
    
    Returns:
        Status message about project structure
    """
    path = _resolve_project_path(project_dir)
    
    path.mkdir(parents=True, exist_ok=True)
    
    project_json = path / "project.json"
    if project_json.exists():
        return _tool(True, f"Project structure OK: {project_json} exists")
    
    # Create minimal project.json
    import uuid
    template = {
        "name": path.name or "GeneratedProject",
        "projectId": str(uuid.uuid4()),
        "description": "Generated UiPath automation",
        "main": "Main.xaml",
        "dependencies": {
            "UiPath.System.Activities": "[26.2.4]",
        },
        "webServices": [],
        "entryPoints": [
            {
                "filePath": "Main.xaml",
                "uniqueId": str(uuid.uuid4()),
                "input": [],
                "output": [],
            }
        ],
        "schemaVersion": "4.0",
        "studioVersion": "26.0.190.0",
        "projectVersion": "1.0.0",
        "runtimeOptions": {
            "autoDispose": False,
            "netFrameworkLazyLoading": False,
            "isPausable": True,
            "isAttended": False,
            "requiresUserInteraction": True,
            "supportsPersistence": False,
            "workflowSerialization": "NewtonsoftJson",
            "excludedLoggedData": ["Private:*", "*password*"],
            "executionType": "Workflow",
            "readyForPiP": False,
            "startsInPiP": False,
            "mustRestoreAllDependencies": True,
            "pipType": "ChildSession",
        },
        "designOptions": {
            "projectProfile": "Developement",
            "outputType": "Process",
            "libraryOptions": {"privateWorkflows": []},
            "processOptions": {"ignoredFiles": []},
            "fileInfoCollection": [],
            "saveToCloud": False,
        },
        "expressionLanguage": "VisualBasic",
        "isTemplate": False,
        "templateProjectData": {},
        "publishData": {},
        "targetFramework": "Windows",
    }
    
    try:
        project_json.write_text(json.dumps(template, indent=2), encoding="utf-8")
        return _tool(True, f"Created project.json at {project_json}")
    except Exception as e:
        return _tool(False, f"Error creating project.json: {e}")


@tool
def query_uipath_docs(question: str) -> str:
    """Query UiPath official documentation using Ask AI.
    
    Use this when:
    - You need authoritative information about UiPath activities
    - Local activity docs don't have enough detail
    - You need to understand activity properties, examples, or best practices
    
    Args:
        question: Question about UiPath (e.g., "What are the properties of GetOutlookMailMessages?")
    
    Returns:
        Answer from UiPath documentation with sources
    """
    import sys
    
    # Add skills path to find the client
    skills_path = Path(__file__).resolve().parent.parent.parent / "skills" / "skills" / "uipath-askai"
    if skills_path.exists():
        sys.path.insert(0, str(skills_path))
        try:
            from uipath_askai_client import UiPathAskAIClient
            
            config_path = skills_path / "uipath_askai_config.json"
            if not config_path.exists():
                return _tool(
                    False,
                    "Error: uipath_askai_config.json not configured. See skills/skills/uipath-askai/UIPATH_ASKAI_SETUP.md",
                )
            
            client = UiPathAskAIClient(str(config_path))
            result = client.ask(question)
            
            if result.get("success"):
                return _tool(True, client.format_response(result))
            else:
                return _tool(False, f"Error querying UiPath docs: {result.get('error', 'Unknown error')}")
        except ImportError as e:
            return _tool(False, f"Error importing UiPath Ask AI client: {e}")
        except Exception as e:
            return _tool(False, f"Error querying UiPath docs: {e}")
        finally:
            if str(skills_path) in sys.path:
                sys.path.remove(str(skills_path))
    
    return _tool(
        False,
        "Error: UiPath Ask AI skill not found. Install it in skills/skills/uipath-askai/",
    )


def get_planning_tools() -> list:
    """Return the list of read-only tools available during planning."""
    return [
        read_file,
        list_directory,
        read_project_json,
        find_activity_info,
        query_uipath_docs,
    ] + get_library_tools()


# Deployment validation constants
VALID_FOLDER_NAME_PATTERN = re.compile(r'^[A-Za-z0-9_\- /]+$')
MAX_FOLDER_NAME_LENGTH = 200


def _validate_folder_name(folder: str) -> Tuple[bool, Optional[str]]:
    """
    Validate folder name for safety and correctness.
    
    Args:
        folder: Folder path to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not folder or not folder.strip():
        return False, "Folder name cannot be empty"
    
    if len(folder) > MAX_FOLDER_NAME_LENGTH:
        return False, f"Folder name too long (max {MAX_FOLDER_NAME_LENGTH} characters)"
    
    if not VALID_FOLDER_NAME_PATTERN.match(folder):
        return False, "Folder name contains invalid characters (use only letters, numbers, spaces, hyphens, underscores, and forward slashes)"
    
    # Check for path traversal attempts
    if ".." in folder:
        return False, "Folder name cannot contain '..' (path traversal not allowed)"
    
    return True, None


def _is_authentication_error(error_message: str) -> bool:
    """
    Detect if error is authentication-related using pattern matching.
    
    Args:
        error_message: Error output from CLI command
        
    Returns:
        True if error indicates authentication failure
    """
    # Comprehensive patterns for auth errors
    auth_patterns = [
        r'\bnot\s+authenticated\b',
        r'\bauthentication\s+(failed|required|error)\b',
        r'\binvalid\s+(token|credentials|auth)\b',
        r'\bexpired\s+token\b',
        r'\bunauthorized\b',
        r'\b401\b',
        r'\b403\s+forbidden\b',
        r'\blogin\s+required\b',
        r'\bmissing\s+(token|credentials)\b'
    ]
    
    error_lower = error_message.lower()
    return any(re.search(pattern, error_lower, re.IGNORECASE) for pattern in auth_patterns)


@tool
def deploy_to_orchestrator(
    project_path: str,
    orchestrator_url: Optional[str] = None,
    tenant_name: Optional[str] = None,
    folder_path: str = "Test",
    process_name: Optional[str] = None
) -> str:
    """
    Deploy a UiPath project to Orchestrator or Studio Web.
    
    This packages the project and deploys it to UiPath Orchestrator (cloud or on-premise).
    Requires UiPath CLI to be installed and authenticated.
    
    Args:
        project_path: Project directory; relative paths use the chat session artifact
            root (same as write_file / read_project_json), absolute paths are used as-is
        orchestrator_url: Orchestrator URL (or use $env:UIPATH_ORCHESTRATOR_URL)
        tenant_name: Tenant name (or use $env:UIPATH_TENANT_NAME)
        folder_path: Target folder in Orchestrator (default: "Test")
        process_name: Name for the process (optional, defaults to project name)
    
    Returns:
        JSON string with deployment status, package path, and steps
        
    Example:
        deploy_to_orchestrator(
            project_path=".",
            orchestrator_url="https://cloud.uipath.com/org/tenant/orchestrator_",
            tenant_name="DefaultTenant",
            folder_path="Prod"
        )
    """
    try:
        path = _resolve_project_path(project_path)
        proj_path = path.resolve()
        
        # Validate folder name first (security check)
        is_valid_folder, folder_error = _validate_folder_name(folder_path)
        if not is_valid_folder:
            return _tool(
                False,
                json.dumps({
                    "success": False,
                    "error": f"Invalid folder name: {folder_error}",
                    "help": "Folder names must contain only letters, numbers, spaces, hyphens, underscores, and forward slashes",
                }),
            )
        
        # Check project exists
        if not (proj_path / "project.json").exists():
            return _tool(
                False,
                json.dumps({
                    "success": False,
                    "error": f"project.json not found at {proj_path}",
                    "help": "Ensure the project is created before deploying",
                }),
            )
        
        # Get config from environment variables (no defaults)
        orch_url = orchestrator_url or os.getenv("UIPATH_ORCHESTRATOR_URL")
        tenant = tenant_name or os.getenv("UIPATH_TENANT_NAME")
        
        if not orch_url:
            return _tool(
                False,
                json.dumps({
                    "success": False,
                    "error": "Missing Orchestrator URL",
                    "help": (
                        "Set environment variable UIPATH_ORCHESTRATOR_URL or provide orchestrator_url parameter.\n\n"
                        "Example (Cloud Orchestrator):\n"
                        "  UIPATH_ORCHESTRATOR_URL=https://cloud.uipath.com/[org]/[tenant]/orchestrator_\n\n"
                        "Example (On-Premise):\n"
                        "  UIPATH_ORCHESTRATOR_URL=https://orchestrator.company.com/[tenant]/orchestrator_"
                    ),
                }),
            )
        
        if not tenant:
            return _tool(
                False,
                json.dumps({
                    "success": False,
                    "error": "Missing tenant name",
                    "help": (
                        "Set environment variable UIPATH_TENANT_NAME or provide tenant_name parameter.\n\n"
                        "Example:\n"
                        "  UIPATH_TENANT_NAME=DefaultTenant"
                    ),
                }),
            )
        
        if not orch_url or not tenant:
            return _tool(
                False,
                json.dumps({
                    "success": False,
                    "error": "Missing Orchestrator URL or tenant name",
                    "help": "Set environment variables: UIPATH_ORCHESTRATOR_URL and UIPATH_TENANT_NAME, or provide as arguments",
                }),
            )
        
        # Read project metadata
        with open(proj_path / "project.json", "r", encoding="utf-8") as f:
            proj_config = json.load(f)
        
        proj_name = proj_config.get("name", proj_path.name)
        proj_version = proj_config.get("projectVersion", "1.0.0")
        proc_name = process_name or proj_name
        
        steps = []
        
        # Step 1: Pack
        steps.append("Packing project...")
        pack_output = proj_path / f"{proj_name}.{proj_version}.nupkg"
        
        pack_cmd = [
            "uipath", "package", "pack",
            str(proj_path),
            "-o", str(pack_output),
            "--outputType", "Process"
        ]
        
        pack_result = subprocess.run(
            pack_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(proj_path)
        )
        
        if pack_result.returncode != 0:
            steps.append(f"Pack failed: {pack_result.stderr[:200]}")
            return _tool(
                False,
                json.dumps({
                    "success": False,
                    "error": f"Packaging failed: {pack_result.stderr}",
                    "steps": steps,
                }),
            )
        
        steps.append(f"Packed successfully: {pack_output.name}")
        
        # Step 2: Deploy
        steps.append(f"Deploying to {orch_url}...")
        
        deploy_cmd = [
            "uipath", "package", "deploy",
            str(pack_output),
            orch_url,
            tenant,
            "--folder", folder_path
        ]
        
        deploy_result = subprocess.run(
            deploy_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(proj_path)
        )
        
        if deploy_result.returncode != 0:
            error_msg = deploy_result.stderr
            steps.append(f"Deploy failed: {error_msg[:200]}")
            
            # Check if it's an authentication error using pattern matching
            if _is_authentication_error(error_msg):
                # Get tenant for help message (don't hardcode)
                tenant_for_help = tenant or "[your-tenant]"
                
                auth_help = (
                    f"Authentication required. Run one of these commands:\n\n"
                    f"For Cloud Orchestrator:\n"
                    f"  uipath auth --cloud --tenant {tenant_for_help}\n\n"
                    f"For On-Premise Orchestrator:\n"
                    f"  uipath auth --base-url {orch_url} --tenant {tenant_for_help}\n\n"
                    f"This will open a browser for interactive authentication.\n"
                    f"Then retry the deployment."
                )
                
                return _tool(
                    False,
                    json.dumps({
                        "success": False,
                        "error": f"Authentication error: {error_msg[:200]}",
                        "steps": steps,
                        "package_created": str(pack_output) if pack_output.exists() else None,
                        "help": auth_help,
                    }),
                )
            
            return _tool(
                False,
                json.dumps({
                    "success": False,
                    "error": f"Deployment failed: {error_msg}",
                    "steps": steps,
                    "package_created": str(pack_output) if pack_output.exists() else None,
                }),
            )
        
        steps.append("Deployed successfully to Orchestrator")
        steps.append(f"Package: {proj_name} v{proj_version}")
        steps.append(f"Folder: {folder_path}")
        steps.append("Next: Create process in Orchestrator UI to assign to robots")
        
        return _tool(
            True,
            json.dumps({
                "success": True,
                "project_name": proj_name,
                "project_version": proj_version,
                "package_path": str(pack_output),
                "orchestrator_url": orch_url,
                "tenant": tenant,
                "folder": folder_path,
                "process_name": proc_name,
                "steps": steps,
                "message": f"Deployment successful! Package '{proj_name}' v{proj_version} deployed to {folder_path}. Create a process in Orchestrator to assign to robots.",
            }),
        )
        
    except FileNotFoundError:
        return _tool(
            False,
            json.dumps({
                "success": False,
                "error": "UiPath CLI not found. Install from: https://docs.uipath.com/automation-cloud/automation-cloud/latest/admin-guide/managing-automation-suite-using-the-cli",
                "steps": ["UiPath CLI not installed"],
            }),
        )
    except subprocess.TimeoutExpired:
        return _tool(
            False,
            json.dumps({
                "success": False,
                "error": "Deployment operation timed out",
                "steps": steps + ["Operation timed out after 120 seconds"],
            }),
        )
    except Exception as e:
        return _tool(
            False,
            json.dumps({
                "success": False,
                "error": str(e),
                "steps": steps + [f"Unexpected error: {str(e)}"],
            }),
        )


def get_skill_execution_tools() -> list:
    """Return the list of tools available during skill execution."""
    return [
        read_file,
        write_file,
        list_directory,
        read_project_json,
        install_package,
        validate_file,        # Static validation
        run_workflow,         # Runtime testing
        run_uip_command,
        find_activity_info,
        validate_and_fix_loop,
        debug_workflow,       # Interactive debugging
        ensure_project_structure,
        query_uipath_docs,
        deploy_to_orchestrator,  # Deploy to Orchestrator/Studio Web
    ] + get_library_tools()
