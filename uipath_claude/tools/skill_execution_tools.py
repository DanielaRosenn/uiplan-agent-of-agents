"""Tools for agentic skill execution.

These tools are bound to the LLM during skill execution, allowing it to
read/write files, run CLI commands, validate workflows, and install packages.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

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
    path = Path(file_path)
    if not path.is_absolute():
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            path = output_root / session_id / file_path
        else:
            path = output_root / file_path
    
    if not path.exists():
        return f"Error: File not found: {file_path}"
    
    try:
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            content = path.read_text(encoding="utf-8")[:MAX_FILE_SIZE]
            return f"{content}\n\n[TRUNCATED - file is {size} bytes, showing first {MAX_FILE_SIZE}]"
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


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
    output_root = _get_output_root()
    session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
    if session_id:
        base = output_root / session_id
    else:
        base = output_root
    
    dest = _resolve_safe_path(base, file_path)
    if dest is None:
        return f"Error: Invalid file path: {file_path}"
    
    # For XAML files, validate XML structure and fix common issues
    if file_path.lower().endswith(".xaml"):
        # Try to fix common XAML issues
        fixed_content = _fix_xaml_content(content)
        
        # Validate XML structure
        xml_error = _validate_xml_structure(fixed_content)
        if xml_error:
            return f"Error: Invalid XAML - {xml_error}. Make sure all XML tags use < and > directly, not &lt; and &gt;."
        
        content = fixed_content
    
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} bytes to {dest}"
    except Exception as e:
        return f"Error writing file: {e}"


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
    path = Path(dir_path)
    if not path.is_absolute():
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            path = output_root / session_id / dir_path
        else:
            path = output_root / dir_path
    
    if not path.exists():
        return f"Error: Directory not found: {dir_path}"
    
    if not path.is_dir():
        return f"Error: Not a directory: {dir_path}"
    
    try:
        matches = list(path.glob(pattern))
        if not matches:
            return f"No files matching '{pattern}' in {dir_path}"
        
        result = []
        for m in sorted(matches)[:100]:  # Limit to 100 results
            if m.is_file():
                try:
                    rel = m.relative_to(path)
                    result.append(str(rel))
                except ValueError:
                    result.append(str(m))
        
        return "\n".join(result) if result else f"No files matching '{pattern}'"
    except Exception as e:
        return f"Error listing directory: {e}"


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
    path = Path(project_dir)
    if not path.is_absolute():
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            path = output_root / session_id / project_dir
        else:
            path = output_root / project_dir
    
    project_json = path / "project.json"
    if not project_json.exists():
        return f"Error: project.json not found in {project_dir}"
    
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
        return json.dumps(summary, indent=2)
    except Exception as e:
        return f"Error reading project.json: {e}"


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
    path = Path(project_dir)
    if not path.is_absolute():
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            path = output_root / session_id / project_dir
        else:
            path = output_root / project_dir
    
    if not (path / "project.json").exists():
        return f"Error: No project.json found in {project_dir}"
    
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
        return "Error: uip CLI not found. Install with: npm install -g @uipath/cli"
    except subprocess.TimeoutExpired:
        return "Error: Package installation timed out after 120s"
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    
    if proc.returncode == 0:
        return f"Successfully installed {package_id}" + (f" version {version}" if version else "")
    
    result = _parse_first_json_payload(output)
    if result and result.get("Message"):
        return f"Error installing package: {result['Message']}"
    
    return f"Error installing package: {output[:500]}"


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
    path = Path(project_dir)
    if not path.is_absolute():
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            path = output_root / session_id / project_dir
        else:
            path = output_root / project_dir
    
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
        return msg
    
    msg = f"Validation failed: {len(result['errors'])} error(s)"
    for e in result["errors"][:10]:
        msg += f"\n  - {e}"
    if result["warnings"]:
        msg += f"\n{len(result['warnings'])} warning(s):"
        for w in result["warnings"][:5]:
            msg += f"\n  - {w}"
    
    if result.get("studio_required"):
        msg += "\n\nNote: Full validation requires UiPath Studio to be running."
    
    return msg


@tool
def run_uip_command(command: str, args: list[str], project_dir: str | None = None) -> str:
    """Run any uip CLI command.
    
    Use this for commands not covered by other tools, such as:
    - uip rpa find-activities --query "GetOutlook"
    - uip rpa get-default-activity-xaml --activity-class-name "..."
    - uip rpa list-instances
    - uip rpa create-project --name "..." --location "..."
    
    Args:
        command: The uip subcommand (e.g., "rpa", "is")
        args: List of arguments for the command
        project_dir: Optional project directory for context
    
    Returns:
        Command output or error message
    """
    uip_cli = _find_uip_cli()
    
    cmd = [uip_cli, command] + args
    
    # Note: --use-studio flag removed as it's not supported by all CLI versions
    
    # Set working directory if project_dir provided
    cwd = None
    if project_dir:
        path = Path(project_dir)
        if not path.is_absolute():
            output_root = _get_output_root()
            session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
            if session_id:
                path = output_root / session_id / project_dir
            else:
                path = output_root / project_dir
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
        return "Error: uip CLI not found. Install with: npm install -g @uipath/cli"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after 60s"
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    
    # Try to extract JSON result if present
    result = _parse_first_json_payload(output)
    if result:
        if result.get("Result") == "Success":
            data = result.get("Data", result)
            return json.dumps(data, indent=2)[:5000]
        elif result.get("Message"):
            return f"Error: {result['Message']}"
    
    # Return raw output (truncated)
    return output[:5000] if output else "(no output)"


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
                return f"Activity: {md_file.stem}\nPackage: {package}\nSource: bundled_docs\n\n{content[:4000]}"
    
    # Fallback to ActivityDiscovery
    from uipath_claude.activities.discovery import ActivityDiscovery
    
    # Determine project path
    if project_dir:
        path = Path(project_dir)
        if not path.is_absolute():
            output_root = _get_output_root()
            session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
            if session_id:
                path = output_root / session_id / project_dir
            else:
                path = output_root / project_dir
    else:
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        path = output_root / session_id if session_id else output_root
    
    discovery = ActivityDiscovery(skills_root)
    info = discovery.find_activity(query, path)
    
    if info is None:
        return f"No documentation found for activity: {query}. Try searching UiPath docs at https://docs.uipath.com/activities"
    
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
    
    return "\n".join(result)


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
    path = Path(project_dir)
    if not path.is_absolute():
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            path = output_root / session_id / project_dir
        else:
            path = output_root / project_dir
    
    result = run_uip_rpa_get_errors(
        str(path.resolve()),
        file_path=file_path,
        use_studio=False,
    )
    
    if result["success"]:
        return f"VALIDATION PASSED: {file_path} has 0 errors"
    
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
    
    return msg


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
    path = Path(project_dir)
    if not path.is_absolute():
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            path = output_root / session_id / project_dir
        else:
            path = output_root / project_dir
    
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
        return "Error: uip CLI not found. Install with: npm install -g @uipath/cli"
    except subprocess.TimeoutExpired:
        return "Error: Workflow execution timed out after 5 minutes"
    
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    
    if proc.returncode == 0:
        return f"Workflow executed successfully.\n\nOutput:\n{output[:2000]}"
    
    return f"Workflow execution failed (exit code {proc.returncode}).\n\nOutput:\n{output[:2000]}"


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
    
    errors = data.get("Errors", [])
    log_entries = data.get("LogEntries", [])
    output_data = data.get("Output", {})
    execution_state = output_data.get("State", "Unknown")
    
    # Filter log entries to only errors/critical unless verbose
    if not verbose:
        log_entries = [
            entry for entry in log_entries
            if entry.get("Severity") in ["Error", "Critical", "Fatal"]
        ]
    
    # Limit to first 5 error entries for token efficiency
    if len(log_entries) > 5 and not verbose:
        log_entries = log_entries[:5]
    
    return {
        "success": is_successful and execution_state == "Completed",
        "error_message": error_message,
        "execution_state": execution_state,
        "errors": errors,
        "log_entries": log_entries,
        "has_more_logs": len(data.get("LogEntries", [])) > len(log_entries)
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
    path = Path(project_dir)
    if not path.is_absolute():
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            path = output_root / session_id / project_dir
        else:
            path = output_root / project_dir
    
    # Check if file exists
    workflow_file = path / file_path
    if not workflow_file.exists():
        return f"Error: Workflow file not found: {workflow_file}"
    
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
    
    # 3. EXECUTE WITH TIMEOUT
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return "Error: uip CLI not found. Install with: npm install -g @uipath/cli"
    except subprocess.TimeoutExpired:
        return f"Error: Workflow execution timed out after {timeout_seconds} seconds. The workflow may be stuck or taking too long."
    
    # 4. PARSE JSON RESPONSE
    output_text = proc.stdout if proc.stdout else proc.stderr
    
    if not output_text:
        return "Error: No output from CLI command. The workflow may not have executed."
    
    parsed = _parse_runtime_response(output_text, verbose)
    
    # 5. FORMAT RESPONSE
    result = _format_runtime_result(parsed, verbose)
    
    # 6. TOKEN EFFICIENCY - Truncate if too long
    if len(result) > 2000 and not verbose:
        result = result[:2000] + "\n\n... (TRUNCATED - use verbose=True for full output)"
    
    return result


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
    path = Path(project_dir)
    if not path.is_absolute():
        output_root = _get_output_root()
        session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
        if session_id:
            path = output_root / session_id / project_dir
        else:
            path = output_root / project_dir
    
    path.mkdir(parents=True, exist_ok=True)
    
    project_json = path / "project.json"
    if project_json.exists():
        return f"Project structure OK: {project_json} exists"
    
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
        return f"Created project.json at {project_json}"
    except Exception as e:
        return f"Error creating project.json: {e}"


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
                return "Error: uipath_askai_config.json not configured. See skills/skills/uipath-askai/UIPATH_ASKAI_SETUP.md"
            
            client = UiPathAskAIClient(str(config_path))
            result = client.ask(question)
            
            if result.get("success"):
                return client.format_response(result)
            else:
                return f"Error querying UiPath docs: {result.get('error', 'Unknown error')}"
        except ImportError as e:
            return f"Error importing UiPath Ask AI client: {e}"
        except Exception as e:
            return f"Error querying UiPath docs: {e}"
        finally:
            if str(skills_path) in sys.path:
                sys.path.remove(str(skills_path))
    
    return "Error: UiPath Ask AI skill not found. Install it in skills/skills/uipath-askai/"


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
    ]
