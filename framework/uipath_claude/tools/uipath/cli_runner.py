"""Subprocess helpers for official uipath CLI (studio package analyze/pack)."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Literal

try:  # audit is best-effort; must never block the runner
    from uipath_claude.audit import append_event as _audit_append
except Exception:  # pragma: no cover - import-time failure tolerated
    def _audit_append(*_a, **_kw):  # type: ignore[no-redef]
        return None


Severity = Literal["error", "warning", "info", "verbose"]


def _emit_cli_event(
    project_dir: str | Path | None,
    *,
    action: str,
    argv: list[str],
    exit_code: int | str,
    stdout: str = "",
    stderr: str = "",
    outcome: str = "",
    notes: str = "",
    studio_attached: bool | str = "unknown",
    validation_passes: list[dict] | None = None,
) -> None:
    if not project_dir:
        return
    _audit_append(
        project_dir,
        {
            "actor": "cli",
            "action": action,
            "command": argv,
            "exit_code": exit_code,
            "stdout_excerpt": stdout,
            "stderr_excerpt": stderr,
            "outcome": outcome,
            "notes": notes,
            "studio_attached": studio_attached,
            "validation_passes": validation_passes or [],
        },
    )


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


_HEADER_COUNT_RE = re.compile(r"^\s*(Errors|Warnings|Diagnostics)\s*\((\d+)\)\s*:\s*$", re.MULTILINE)


def _parse_get_errors_message(message: str, *, min_severity: Severity) -> tuple[list[str], list[str]]:
    """Parse the textual `Errors (N):` / `Warnings (N):` block returned by get-errors.

    When called with `--min-severity error`, the CLI only emits an `Errors (N):`
    block; every `- ` bullet under that header is treated as an error regardless of
    the prose inside it (the previous "contains the word warning" heuristic was the
    source of false negatives). When called with broader severities we look for a
    `Warnings (N):` header to split.
    """
    errors: list[str] = []
    warnings: list[str] = []
    if not message:
        return errors, warnings

    if "No diagnostics found" in message:
        return errors, warnings

    # Find headers and slice the message into sections per header.
    headers = list(_HEADER_COUNT_RE.finditer(message))
    if not headers:
        # Fallback: every "- " bullet is an error in error-only mode.
        for line in message.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                errors.append(stripped[2:].strip())
        return errors, warnings

    for idx, match in enumerate(headers):
        kind = match.group(1).lower()
        start = match.end()
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(message)
        section = message[start:end]
        for line in section.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- "):
                continue
            item = stripped[2:].strip()
            if kind == "warnings":
                warnings.append(item)
            else:
                # "errors" or "diagnostics" both treated as errors when min_severity=error
                if min_severity == "error":
                    errors.append(item)
                else:
                    errors.append(item)
    return errors, warnings


def _detect_studio_required(output: str) -> bool:
    """Heuristic: is Studio integration blocked / unreachable?"""
    return (
        "IInteropProjectService" in output
        or "IAutopilotValidationService" in output
        or "DependencyResolutionException" in output
        or ("Studio" in output and "not" in output.lower())
    )


def studio_available(project_path: str | Path | None = None, *, timeout: int = 20) -> bool:
    """Lightweight probe to detect whether the Studio backend is reachable.

    We invoke `uip rpa find-activities --query SetTransactionStatus --output json`
    (cheap, no project needed) and treat a successful JSON parse as evidence the
    Studio process / IPC bridge is up. False on FileNotFoundError, timeout, or
    `IInteropProjectService` failures.
    """
    uip_cli = _find_uip_cli()
    cmd = [uip_cli, "rpa", "find-activities", "--query", "SetTransactionStatus", "--output", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    if _detect_studio_required(output):
        return False
    payload = _parse_first_json_payload(output)
    return bool(payload and payload.get("Result") == "Success")


def run_uip_rpa_get_errors(
    project_path: str | Path,
    *,
    file_path: str | None = None,
    timeout: int = 120,
    use_studio: bool = True,
    min_severity: Severity = "error",
    passes: int = 2,
    force_revalidate: bool = True,
) -> dict:
    """Run `uip rpa get-errors` (potentially multiple passes) against a project.

    The Studio IPC behind get-errors is stateful; a single call right after a write
    can return a stale "No diagnostics found" while the next one reports the real
    compile errors. We therefore run the CLI ``passes`` times by default and return
    the **union** of errors so a stale-cache pass cannot mask a real failure.

    Args:
        project_path: Path to the UiPath project directory.
        file_path: Optional specific file (relative to the project).
        timeout: Per-pass timeout in seconds.
        use_studio: Forward `--use-studio` to drive the live Studio backend.
        min_severity: Forwarded to `--min-severity` (default `error`).
        passes: How many times to call get-errors; results are unioned. Minimum 1.
        force_revalidate: When True, never pass `--skip-validation`; we always want
            the freshest diagnostics. The flag is here so callers can opt-out
            explicitly if they ever need a quick probe (e.g. studio_available()).

    Returns dict with:
        success, errors, warnings, raw_output, studio_required, passes_run
    """
    path = str(Path(project_path).resolve())
    uip_cli = _find_uip_cli()

    base_cmd = [uip_cli, "rpa", "get-errors", "--project-dir", path, "--output", "json"]
    if file_path:
        base_cmd.extend(["--file-path", file_path])
    # Note: `--use-studio` is NOT a valid flag on `uip rpa get-errors` in current
    # CLI builds (it raises `unknown option '--use-studio'`). The CLI always uses
    # the running Studio backend when available. The parameter is kept for API
    # compatibility with callers that previously forwarded it.
    _ = use_studio
    if min_severity:
        base_cmd.extend(["--min-severity", min_severity])
    if not force_revalidate:
        base_cmd.append("--skip-validation")

    n_passes = max(1, int(passes))
    union_errors: list[str] = []
    union_warnings: list[str] = []
    raw_outputs: list[str] = []
    studio_required = False
    passes_run = 0
    last_returncode: int | None = None
    pass_records: list[dict] = []

    for attempt in range(1, n_passes + 1):
        try:
            proc = subprocess.run(
                base_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            err = "uip CLI not found. Install with: npm install -g @uipath/cli"
            _emit_cli_event(
                project_path,
                action="get_errors",
                argv=base_cmd,
                exit_code="missing-cli",
                stderr=err,
                outcome="error",
            )
            return {
                "success": False,
                "errors": [err],
                "warnings": [],
                "raw_output": "",
                "studio_required": False,
                "passes_run": passes_run,
            }
        except subprocess.TimeoutExpired:
            err = f"Validation timed out after {timeout}s on pass {attempt}/{n_passes}"
            _emit_cli_event(
                project_path,
                action="get_errors",
                argv=base_cmd,
                exit_code="timeout",
                stderr=err,
                outcome="needs_human",
                notes=f"pass={attempt}",
            )
            return {
                "success": False,
                "errors": [err],
                "warnings": [],
                "raw_output": "\n".join(raw_outputs),
                "studio_required": studio_required,
                "passes_run": passes_run,
            }

        output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
        raw_outputs.append(output)
        last_returncode = proc.returncode
        passes_run += 1
        studio_required = studio_required or _detect_studio_required(output)

        pass_errors: list[str] = []
        pass_warnings: list[str] = []
        parsed = _parse_first_json_payload(output)
        if parsed is None:
            if proc.returncode != 0:
                pass_errors.append(proc.stderr or output or "Validation failed")
        elif parsed.get("Result") == "Success":
            data = parsed.get("Data", {}) or {}
            # Prefer structured diagnostics if the CLI ever emits them.
            structured = data.get("Diagnostics") or data.get("diagnostics")
            if isinstance(structured, list):
                for diag in structured:
                    sev = str(diag.get("Severity") or diag.get("severity") or "").lower()
                    msg = str(diag.get("Message") or diag.get("message") or "").strip()
                    if not msg:
                        continue
                    if sev == "warning":
                        pass_warnings.append(msg)
                    else:
                        pass_errors.append(msg)
            else:
                msg = data.get("message", "")
                pe, pw = _parse_get_errors_message(msg, min_severity=min_severity)
                pass_errors.extend(pe)
                pass_warnings.extend(pw)
        else:
            error_msg = parsed.get("Message", "Unknown error")
            if isinstance(error_msg, str):
                try:
                    nested = json.loads(error_msg)
                    inner = nested.get("errorMessage")
                    if isinstance(inner, str) and inner.strip():
                        error_msg = inner
                except Exception:
                    pass
            pass_errors.append(str(error_msg))

        union_errors.extend(pass_errors)
        union_warnings.extend(pass_warnings)
        pass_records.append(
            {
                "pass": attempt,
                "errors": list(pass_errors),
                "warnings": list(pass_warnings),
            }
        )

    # De-duplicate while preserving order
    seen: set[str] = set()
    deduped_errors = [e for e in union_errors if not (e in seen or seen.add(e))]
    seen2: set[str] = set()
    deduped_warnings = [w for w in union_warnings if not (w in seen2 or seen2.add(w))]

    success = len(deduped_errors) == 0
    outcome = "pass" if success else "needs_llm_fix"
    _emit_cli_event(
        project_path,
        action="get_errors",
        argv=base_cmd,
        exit_code=last_returncode if last_returncode is not None else "",
        stdout="\n\n--- pass break ---\n\n".join(raw_outputs),
        outcome=outcome,
        notes=f"passes_run={passes_run} min_severity={min_severity}",
        validation_passes=pass_records,
    )

    return {
        "success": success,
        "errors": deduped_errors,
        "warnings": deduped_warnings,
        "raw_output": "\n\n--- pass break ---\n\n".join(raw_outputs),
        "studio_required": studio_required,
        "passes_run": passes_run,
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
