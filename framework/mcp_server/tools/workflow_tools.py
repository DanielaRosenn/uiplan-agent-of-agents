"""Workflow validation, execution, and project management MCP tools."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.types import Tool, ToolAnnotations

def _ro(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True)


def _ro_idempotent(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True, idempotentHint=True)


def _destructive(title: str, idempotent: bool = False) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=idempotent,
    )

from uipath_claude.tools import session_gate
from uipath_claude.tools.deploy_tool import (
    deploy_to_orchestrator as _deploy,
    publish_project as _publish_project,
)
from uipath_claude.tools.skill_execution_tools import (
    build_and_verify_workflow as _build_and_verify_workflow,
    create_project as _create_project,
    debug_workflow as _debug_workflow,
    ensure_project_structure as _ensure_project_structure,
    environment_probe as _environment_probe,
    install_package as _install_package,
    list_directory as _list_directory,
    read_file as _read_file,
    read_project_json as _read_project_json,
    resolve_write_destination as _resolve_write_destination,
    run_uip_command as _run_uip_command,
    run_workflow as _run_workflow,
    validate_and_fix_loop as _validate_and_fix_loop,
    validate_file as _validate_file,
    write_file as _write_file,
)


def _resolved_write_path(file_path: str) -> str:
    """Best-effort resolved string path for ``file_path`` (gate keying)."""
    resolved = _resolve_write_destination(file_path)
    return str(resolved) if resolved is not None else file_path


_GATED_DIRTY_EXTENSIONS = {".xaml", ".cs", ".json", ".uiproj"}


def _project_dir_for(arguments: dict[str, Any], file_key: str | None = None) -> str | None:
    """Best-effort resolution of a project directory from tool arguments."""
    pd = arguments.get("project_dir") or arguments.get("project_path")
    if pd:
        return str(pd)
    if file_key:
        path = arguments.get(file_key)
        if path:
            resolved_path = _resolved_write_path(str(path))
            resolved = session_gate._project_dir_for_file(resolved_path)
            if resolved:
                return resolved
    return None


def _gate_block_or_text(
    project_dir: str | None,
    calling_tool: str,
    allow_unverified: bool,
) -> str | None:
    """Return a tool-error string when the gate blocks ``calling_tool``."""
    if not project_dir:
        return None
    try:
        session_gate.require_verified(
            project_dir, calling_tool, allow_unverified=allow_unverified
        )
    except session_gate.GateError as exc:
        return (
            f"[BLOCKED] {exc}\n"
            "Run uipath_workflow_build_and_verify until success=true, "
            "or pass allow_unverified=true to override."
        )
    return None


def _design_block_or_text(
    project_dir: str | None,
    calling_tool: str,
    allow_unapproved: bool,
) -> str | None:
    """Return a tool-error string when the design gate blocks ``calling_tool``."""
    if not project_dir:
        return None
    try:
        session_gate.require_approved_design(
            project_dir, calling_tool, allow_unapproved=allow_unapproved
        )
    except session_gate.GateError as exc:
        return f"[BLOCKED] {exc}"
    return None


def _plan_gate_block_or_text(
    project_dir: str | None,
    calling_tool: str,
) -> str | None:
    """Opt-in plan-acceptance gate (UIPATH_PLAN_GATE=1)."""
    try:
        from mcp_server.tools.plan_tools import require_accepted_plan
    except Exception:
        return None
    try:
        verdict = require_accepted_plan(project_dir)
    except Exception:
        return None
    if verdict.get("allowed"):
        return None
    return (
        f"[BLOCKED] {calling_tool}: UIPATH_PLAN_GATE=1 and no accepted plan "
        "was found. Accept a plan via uipath_plan_accept (or disable the gate)."
    )


def _maybe_mark_dirty_after_write(file_path: str, write_result: Any) -> None:
    """Mark the owning project dirty when a write to a gated file succeeded."""
    if not isinstance(write_result, str) or not write_result.startswith("[OK]"):
        return
    suffix = Path(file_path).suffix.lower()
    if suffix not in _GATED_DIRTY_EXTENSIONS:
        return
    project_dir = session_gate._project_dir_for_file(file_path)
    if project_dir:
        session_gate.mark_dirty(project_dir, file_path)


def _maybe_mark_verified_after_build(project_dir: str, build_result: Any) -> None:
    """Clear the dirty flag when build_and_verify reports success=true."""
    if not isinstance(build_result, str):
        return
    if not build_result.startswith("[OK]"):
        return
    verdict = "pass"
    try:
        for line in build_result.splitlines():
            if line.startswith("BUILD+VERIFY"):
                for token in line.split():
                    if token.startswith("verdict="):
                        verdict = token.split("=", 1)[1]
                        break
                break
    except Exception:
        pass
    if verdict != "pass":
        return
    session_gate.mark_verified(project_dir, verdict=verdict)


def get_workflow_tools() -> list[Tool]:
    """Return workflow-related MCP tools."""
    return [
        Tool(
            name="uipath_workflow_read_file",
            description=(
                "Read the UTF-8 contents of any file by absolute or "
                "project-relative path. Read-only; no UiPath CLI invoked. Use "
                "before editing XAML, project.json, or .cs files so subsequent "
                "writes preserve unrelated content."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or project-relative path to the file.",
                    },
                },
                "required": ["file_path"],
            },
            annotations=_ro("Read file"),
        ),
        Tool(
            name="uipath_workflow_write_file",
            description=(
                "Write content to a file in a UiPath project. "
                "DESIGN GATE: writes are rejected with [BLOCKED] when the "
                "owning project (nearest project.json) does not have an "
                "approved design. Submit one via uipath_design_propose and "
                "have the user approve via uipath_design_approve first. Ask "
                "the user (e.g. via Cursor's AskQuestion) to confirm the "
                "design choices before proposing. "
                "AFTER any write to a XAML, .cs, or project.json file the "
                "MCP session gate marks the project DIRTY: subsequent "
                "uipath_workflow_run / _debug / _install_package / _deploy "
                "/ _run_command calls will be rejected with [BLOCKED] until "
                "uipath_workflow_build_and_verify returns success=true and "
                "verdict='pass'. Do not report the task complete before then. "
                "SCAFFOLD GUARD: writes to project.json / project.uiproj are "
                "rejected unless allow_scaffold_overwrite=true. Use "
                "uipath_workflow_create_project for new projects and "
                "uipath_workflow_install_package to add or change packages, "
                "and run uipath_workflow_environment_probe first to learn "
                "the local Studio's installed package versions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or project-relative path to the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file body to write (overwrites existing file).",
                    },
                    "allow_scaffold_overwrite": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Set true ONLY when the user explicitly asks to "
                            "overwrite project.json / project.uiproj."
                        ),
                    },
                    "allow_unapproved": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Bypass the design-approval gate for this single "
                            "call. Use only when the user explicitly waives "
                            "the design step."
                        ),
                    },
                },
                "required": ["file_path", "content"],
            },
            annotations=ToolAnnotations(
                title="Write file in UiPath project",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=True,
            ),
        ),
        Tool(
            name="uipath_workflow_list_directory",
            description=(
                "List files and subdirectories under a path, optionally filtered "
                "by a glob pattern. Read-only. Use to discover XAML files, "
                ".cs files, or project layout before reading or editing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Absolute or project-relative directory path.",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g. '*.xaml').",
                        "default": "*",
                    },
                },
                "required": ["directory_path"],
            },
            annotations=_ro("List directory"),
        ),
        Tool(
            name="uipath_workflow_read_project",
            description=(
                "Read and JSON-parse project.json from a UiPath project. "
                "Read-only. Use to inspect declared dependencies and entry "
                "point before calling uipath_workflow_install_package or "
                "uipath_workflow_validate."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root containing project.json (default: current dir).",
                        "default": ".",
                    },
                },
            },
            annotations=_ro("Read project.json"),
        ),
        Tool(
            name="uipath_workflow_install_package",
            description=(
                "Install or update a NuGet package in a UiPath project via "
                "'uip rpa install-or-update-packages'. Mutates project.json and "
                "the local packages folder. Run uipath_workflow_environment_probe "
                "first so the chosen version matches Studio's installed packages, "
                "and follow with uipath_workflow_build_and_verify to confirm. "
                "GATED: blocked by the MCP session gate when the project has "
                "unverified writes; the call returns [BLOCKED] until "
                "uipath_workflow_build_and_verify reports success=true. Set "
                "allow_unverified=true only for explicit human override."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root containing project.json.",
                    },
                    "package_id": {
                        "type": "string",
                        "description": "NuGet package id (e.g. UiPath.System.Activities).",
                    },
                    "version": {
                        "type": "string",
                        "description": "Optional package version; default is latest compatible.",
                    },
                    "allow_unverified": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Bypass the session gate. Use only when the user "
                            "explicitly asks to override the dirty-state block."
                        ),
                    },
                    "allow_unapproved": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Bypass the design-approval gate for this call."
                        ),
                    },
                },
                "required": ["project_dir", "package_id"],
            },
            annotations=_destructive("Install NuGet package"),
        ),
        Tool(
            name="uipath_workflow_validate",
            description=(
                "Validate a single XAML workflow via 'uip rpa get-errors' and "
                "return the error list. Read-only and idempotent: surfaces errors "
                "but writes nothing. Prefer uipath_workflow_build_and_verify for "
                "the end-to-end validate+run+fix loop; use this only for a "
                "single static check, or uipath_workflow_validate_loop when you "
                "want auto-fix writes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root containing project.json.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the .xaml workflow file to validate.",
                    },
                },
                "required": ["project_dir", "file_path"],
            },
            annotations=_ro_idempotent("Validate workflow (read-only)"),
        ),
        Tool(
            name="uipath_workflow_validate_loop",
            description=(
                "DEPRECATED NAME: kept for backward compatibility. "
                "Calls uipath_workflow_build_and_verify with "
                "run_after_validate=false. Prefer "
                "uipath_workflow_build_and_verify directly so you also get "
                "runtime execution and dependency-mismatch detection."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root containing project.json.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the .xaml workflow file.",
                    },
                    "max_attempts": {
                        "type": "integer",
                        "description": "Max validate-then-fix iterations.",
                        "default": 5,
                    },
                },
                "required": ["project_dir", "file_path"],
            },
            annotations=_destructive("Validate and auto-fix loop"),
        ),
        Tool(
            name="uipath_workflow_build_and_verify",
            description=(
                "Build, validate, headless-run, and Studio-debug a workflow in a "
                "single server-side LOOP. Canonical 'did it actually work' tool "
                "and the only way to clear the MCP session gate. Pipeline per "
                "iteration: probe Studio + installed packages (with optional "
                "auto-install of mismatched packages) -> uip rpa get-errors over "
                "every .xaml -> if clean and run_after_validate=true execute the "
                "workflow headless -> if a Studio instance is detected and "
                "studio_debug_after_run=true also start a Studio debug session. "
                "Returns success=true and verdict='pass' ONLY when every step "
                "succeeds. The loop keeps iterating up to max_attempts when it "
                "can make automatic progress (e.g. just installed a package); "
                "for LLM-driven fixes it returns early so the agent can patch and "
                "re-call. After ANY write_file / install_package you MUST call "
                "this tool until verdict='pass' before claiming the task done."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root containing project.json.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": (
                            "Optional. Path to a single .xaml workflow file. "
                            "When omitted, every .xaml workflow under "
                            "project_dir is validated; runtime execution "
                            "still targets the project's main entry point."
                        ),
                    },
                    "max_attempts": {
                        "type": "integer",
                        "description": "Max loop iterations before returning.",
                        "default": 5,
                    },
                    "run_after_validate": {
                        "type": "boolean",
                        "description": "If true, also execute the workflow once validation is clean.",
                        "default": True,
                    },
                    "input_arguments": {
                        "type": "string",
                        "description": "Optional JSON string of input arguments forwarded to run_workflow.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Per-run timeout when run_after_validate=true.",
                        "default": 60,
                    },
                    "auto_install_packages": {
                        "type": "boolean",
                        "description": (
                            "When true (default), the loop attempts to resolve "
                            "dependency mismatches via install_package itself."
                        ),
                        "default": True,
                    },
                    "studio_debug_after_run": {
                        "type": "boolean",
                        "description": (
                            "When true (default), also attach a UiPath Studio "
                            "debug session after a successful headless run, "
                            "when a Studio instance is detected."
                        ),
                        "default": True,
                    },
                    "require_studio_debug": {
                        "type": "boolean",
                        "description": (
                            "When true (default), the verify gate refuses to "
                            "report success=true unless an attached Studio "
                            "debug pass also ran. If Studio is unavailable, "
                            "the call returns verdict='needs_human' with "
                            "next_action='start_studio_or_waive'. Set false "
                            "only when the user explicitly waives the Studio "
                            "debug step (e.g. CI host without Studio)."
                        ),
                        "default": True,
                    },
                },
                "required": ["project_dir"],
            },
            annotations=_destructive("Build, validate, run, debug and report fixes"),
        ),
        Tool(
            name="uipath_workflow_environment_probe",
            description=(
                "Probe the local UiPath Studio environment and installed "
                "packages (uip rpa list-instances + list-packages). Call "
                "this BEFORE choosing activity packages or creating / "
                "editing project.json so dependencies match the local "
                "Studio install. Reports any detected dependency mismatches "
                "(e.g. legacy UiPath.Core.Activities next to modern "
                "UiPath.System.Activities)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": (
                            "Optional project directory. If omitted, only "
                            "Studio instances are reported."
                        ),
                    },
                },
            },
            annotations=_ro("Probe Studio environment"),
        ),
        Tool(
            name="uipath_workflow_create_project",
            description=(
                "Create a UiPath project via 'uip rpa create-project'. Use "
                "this INSTEAD of writing project.json by hand: the CLI "
                "generates a project.json whose dependencies match the local "
                "Studio install, avoiding legacy-vs-modern dependency "
                "mismatches that occur when an LLM hand-pins package "
                "versions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Parent directory for the new project folder.",
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name of the new project folder created under project_dir.",
                    },
                    "project_type": {
                        "type": "string",
                        "enum": ["process", "library", "coded"],
                        "description": "UiPath project kind: process, library, or coded.",
                        "default": "process",
                    },
                    "auto_verify": {
                        "type": "boolean",
                        "description": (
                            "When true (default), run "
                            "uipath_workflow_build_and_verify on the new "
                            "project (static validation only) and append "
                            "the result. Set false to skip."
                        ),
                        "default": True,
                    },
                },
                "required": ["project_dir", "project_name"],
            },
            annotations=_destructive("Create UiPath project", idempotent=True),
        ),
        Tool(
            name="uipath_workflow_run",
            description=(
                "Execute a workflow once via 'uip rpa run-file'. Destructive: "
                "any side effects of the workflow (HTTP calls, file writes, "
                "Orchestrator queue items) happen. Validate first with "
                "uipath_workflow_validate or uipath_workflow_build_and_verify; "
                "use uipath_workflow_debug for an attached Studio debug session. "
                "GATED: blocked by the MCP session gate when the project has "
                "unverified writes; the call returns [BLOCKED] until "
                "uipath_workflow_build_and_verify reports success=true."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root containing project.json.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the .xaml workflow to run.",
                    },
                    "input_arguments": {
                        "type": "string",
                        "description": "JSON string of input arguments passed to the workflow.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Hard timeout for the run.",
                        "default": 60,
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "If true, request verbose output from uip.",
                        "default": False,
                    },
                    "allow_unverified": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Bypass the session gate. Use only when the user "
                            "explicitly asks to override the dirty-state block."
                        ),
                    },
                },
                "required": ["project_dir", "file_path"],
            },
            annotations=_destructive("Run workflow"),
        ),
        Tool(
            name="uipath_workflow_debug",
            description=(
                "Start a workflow in debug mode via 'uip rpa run-file StartDebugging', "
                "attaching to a running UiPath Studio if present. Destructive: "
                "the workflow executes. Prefer uipath_workflow_run for headless "
                "runs in CI; use this when stepping through in Studio. "
                "GATED: blocked by the MCP session gate when the project has "
                "unverified writes; the call returns [BLOCKED] until "
                "uipath_workflow_build_and_verify reports success=true."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root containing project.json.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the .xaml workflow to debug.",
                    },
                    "allow_unverified": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Bypass the session gate. Use only when the user "
                            "explicitly asks to override the dirty-state block."
                        ),
                    },
                },
                "required": ["project_dir", "file_path"],
            },
            annotations=_destructive("Debug workflow in Studio"),
        ),
        Tool(
            name="uipath_workflow_ensure_project",
            description=(
                "Confirm a project.json exists under project_dir. Returns "
                "success when present and a clear error pointing at "
                "uipath_workflow_create_project when absent (this tool no "
                "longer hand-writes a minimal project.json - that caused "
                "Studio dependency mismatches). Use "
                "uipath_workflow_create_project to scaffold a new project."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root path to check.",
                    },
                    "project_name": {
                        "type": "string",
                        "description": "If set, checks project_dir/project_name instead.",
                    },
                },
                "required": ["project_dir"],
            },
            annotations=_ro_idempotent("Check project.json exists"),
        ),
        Tool(
            name="uipath_workflow_run_command",
            description=(
                "Escape hatch: invoke an arbitrary uip CLI subcommand. Destructive "
                "by default since uip can mutate the project. Prefer the specific "
                "tools (uipath_workflow_validate, _run, _install_package, _deploy, "
                "_create_project) when one exists; only reach for this when no "
                "wrapper covers the command you need. "
                "GATED: blocked by the MCP session gate when project_dir has "
                "unverified writes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "First uip token (e.g. 'rpa', 'orchestrator').",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Args after command, e.g. ['get-errors', '--project-dir', '.'].",
                    },
                    "project_dir": {
                        "type": "string",
                        "description": "Working directory the uip command runs in.",
                    },
                    "allow_unverified": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Bypass the session gate. Use only when the user "
                            "explicitly asks to override the dirty-state block."
                        ),
                    },
                },
                "required": ["command", "args"],
            },
            annotations=_destructive("Run arbitrary uip command"),
        ),
        Tool(
            name="uipath_workflow_deploy",
            description=(
                "Pack the project and publish it to UiPath Orchestrator, "
                "optionally creating a Process. Destructive and network-dependent: "
                "requires an Orchestrator URL plus tenant, and uses ambient uip "
                "auth credentials. Returns a JSON string with the publish result. "
                "GATED: blocked by the MCP session gate when the project has "
                "unverified writes; the call returns [BLOCKED] until "
                "uipath_workflow_build_and_verify reports success=true."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the UiPath project to pack and publish.",
                    },
                    "orchestrator_url": {
                        "type": "string",
                        "description": "Base URL of the Orchestrator instance.",
                    },
                    "tenant_name": {
                        "type": "string",
                        "description": "Orchestrator tenant name.",
                    },
                    "folder_path": {
                        "type": "string",
                        "description": "Orchestrator folder path to publish into.",
                        "default": "Shared",
                    },
                    "account_name": {
                        "type": "string",
                        "description": "Cloud Orchestrator account name (for cloud tenants).",
                    },
                    "process_name": {
                        "type": "string",
                        "description": "Process display name; defaults to the project name.",
                    },
                    "create_process": {
                        "type": "boolean",
                        "description": "If true, create a Process for the package.",
                        "default": True,
                    },
                    "environment": {
                        "type": "string",
                        "description": "Optional environment to associate with the process.",
                    },
                    "project_type": {
                        "type": "string",
                        "enum": ["process", "maestro"],
                        "default": "process",
                        "description": (
                            "Project family. 'process' uses uip solution pack/publish + "
                            "uip or processes create. 'maestro' uses uip flow pack + "
                            "uip solution publish + uip flow process create."
                        ),
                    },
                    "allow_unverified": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Bypass the session gate. Use only when the user "
                            "explicitly asks to deploy unverified changes."
                        ),
                    },
                },
                "required": ["project_path", "orchestrator_url", "tenant_name"],
            },
            annotations=_destructive("Deploy project to Orchestrator"),
        ),
        Tool(
            name="uipath_workflow_publish",
            description=(
                "Pack and publish a UiPath project to Orchestrator without creating "
                "a Process. Wraps the modern uip CLI (uip solution pack/publish for "
                "RPA, uip flow pack + uip solution publish for Maestro). Returns the "
                "package path and CLI output. GATED by the MCP session gate; blocked "
                "until uipath_workflow_build_and_verify reports success."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Path to the project directory to pack and publish.",
                    },
                    "project_type": {
                        "type": "string",
                        "enum": ["process", "maestro"],
                        "default": "process",
                    },
                    "allow_unverified": {
                        "type": "boolean",
                        "default": False,
                        "description": "Bypass the session gate.",
                    },
                },
                "required": ["project_dir"],
            },
            annotations=_destructive("Publish project package to Orchestrator"),
        ),
        Tool(
            name="uipath_workflow_session_status",
            description=(
                "Inspect the per-project verification gate. Read-only. Reports "
                "whether the gate is enabled (UIPATH_MCP_GATE_ENABLED) and the "
                "current status for project_dir (unknown / dirty / verified) "
                "plus the files that triggered the dirty flag and the last "
                "verify outcome. Pass no project_dir to dump every tracked "
                "project. Use this when a tool returns [BLOCKED] to confirm "
                "what changed and re-run uipath_workflow_build_and_verify."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": (
                            "Optional project directory to inspect. Omit for "
                            "a full snapshot of every tracked project."
                        ),
                    },
                },
            },
            annotations=_ro("Session gate status"),
        ),
    ]


async def call_workflow_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Dispatch workflow MCP tools to LangChain tool implementations."""
    if name == "uipath_workflow_read_file":
        return _read_file.invoke({"file_path": arguments["file_path"]})

    if name == "uipath_workflow_write_file":
        resolved = _resolved_write_path(arguments["file_path"])
        owning_project = session_gate._project_dir_for_file(resolved)
        blocked = _design_block_or_text(
            owning_project,
            "uipath_workflow_write_file",
            bool(arguments.get("allow_unapproved", False)),
        )
        if blocked:
            return blocked
        blocked = _plan_gate_block_or_text(owning_project, "uipath_workflow_write_file")
        if blocked:
            return blocked
        result = _write_file.invoke(
            {
                "file_path": arguments["file_path"],
                "content": arguments["content"],
                "allow_scaffold_overwrite": bool(
                    arguments.get("allow_scaffold_overwrite", False)
                ),
            }
        )
        _maybe_mark_dirty_after_write(resolved, result)
        return result

    if name == "uipath_workflow_list_directory":
        return _list_directory.invoke(
            {
                "dir_path": arguments["directory_path"],
                "pattern": arguments.get("pattern", "*"),
            }
        )

    if name == "uipath_workflow_read_project":
        return _read_project_json.invoke({"project_dir": arguments.get("project_dir", ".")})

    if name == "uipath_workflow_install_package":
        blocked = _design_block_or_text(
            _project_dir_for(arguments),
            "uipath_workflow_install_package",
            bool(arguments.get("allow_unapproved", False)),
        )
        if blocked:
            return blocked
        blocked = _gate_block_or_text(
            _project_dir_for(arguments),
            "uipath_workflow_install_package",
            bool(arguments.get("allow_unverified", False)),
        )
        if blocked:
            return blocked
        blocked = _plan_gate_block_or_text(
            _project_dir_for(arguments), "uipath_workflow_install_package"
        )
        if blocked:
            return blocked
        payload = {
            "project_dir": arguments["project_dir"],
            "package_id": arguments["package_id"],
        }
        if arguments.get("version"):
            payload["version"] = arguments["version"]
        result = _install_package.invoke(payload)
        if isinstance(result, str) and result.startswith("[OK]"):
            pd = session_gate._normalize(arguments["project_dir"])
            session_gate.mark_dirty(pd, "<install_package>")
        return result

    if name == "uipath_workflow_validate":
        return _validate_file.invoke(
            {"project_dir": arguments["project_dir"], "file_path": arguments["file_path"]}
        )

    if name == "uipath_workflow_validate_loop":
        return _validate_and_fix_loop.invoke(
            {
                "project_dir": arguments["project_dir"],
                "file_path": arguments["file_path"],
                "max_attempts": int(arguments.get("max_attempts", 5)),
            }
        )

    if name == "uipath_workflow_build_and_verify":
        payload: dict[str, Any] = {
            "project_dir": arguments["project_dir"],
            "max_attempts": int(arguments.get("max_attempts", 5)),
            "run_after_validate": bool(arguments.get("run_after_validate", True)),
        }
        if arguments.get("file_path"):
            payload["file_path"] = arguments["file_path"]
        if arguments.get("input_arguments") is not None:
            payload["input_arguments"] = arguments["input_arguments"]
        if arguments.get("timeout_seconds") is not None:
            payload["timeout_seconds"] = int(arguments["timeout_seconds"])
        if arguments.get("auto_install_packages") is not None:
            payload["auto_install_packages"] = bool(arguments["auto_install_packages"])
        if arguments.get("studio_debug_after_run") is not None:
            payload["studio_debug_after_run"] = bool(arguments["studio_debug_after_run"])
        if arguments.get("require_studio_debug") is not None:
            payload["require_studio_debug"] = bool(arguments["require_studio_debug"])
        result = _build_and_verify_workflow.invoke(payload)
        _maybe_mark_verified_after_build(arguments["project_dir"], result)
        return result

    if name == "uipath_workflow_environment_probe":
        return _environment_probe.invoke(
            {"project_dir": arguments.get("project_dir")}
        )

    if name == "uipath_workflow_create_project":
        return _create_project.invoke(
            {
                "project_dir": arguments["project_dir"],
                "project_name": arguments["project_name"],
                "project_type": arguments.get("project_type", "process"),
                "auto_verify": bool(arguments.get("auto_verify", True)),
            }
        )

    if name == "uipath_workflow_run":
        blocked = _gate_block_or_text(
            _project_dir_for(arguments),
            "uipath_workflow_run",
            bool(arguments.get("allow_unverified", False)),
        )
        if blocked:
            return blocked
        payload: dict[str, Any] = {
            "project_dir": arguments["project_dir"],
            "file_path": arguments["file_path"],
        }
        if arguments.get("input_arguments") is not None:
            payload["input_arguments"] = arguments["input_arguments"]
        if arguments.get("timeout_seconds") is not None:
            payload["timeout_seconds"] = int(arguments["timeout_seconds"])
        if arguments.get("verbose") is not None:
            payload["verbose"] = bool(arguments["verbose"])
        return _run_workflow.invoke(payload)

    if name == "uipath_workflow_debug":
        blocked = _gate_block_or_text(
            _project_dir_for(arguments),
            "uipath_workflow_debug",
            bool(arguments.get("allow_unverified", False)),
        )
        if blocked:
            return blocked
        return _debug_workflow.invoke(
            {"project_dir": arguments["project_dir"], "file_path": arguments["file_path"]}
        )

    if name == "uipath_workflow_ensure_project":
        base = Path(arguments["project_dir"]).expanduser()
        if arguments.get("project_name"):
            target = (base / arguments["project_name"]).resolve()
            target.mkdir(parents=True, exist_ok=True)
            project_dir = str(target)
        else:
            project_dir = str(base.resolve())
        return _ensure_project_structure.invoke({"project_dir": project_dir})

    if name == "uipath_workflow_run_command":
        blocked = _gate_block_or_text(
            _project_dir_for(arguments),
            "uipath_workflow_run_command",
            bool(arguments.get("allow_unverified", False)),
        )
        if blocked:
            return blocked
        return _run_uip_command.invoke(
            {
                "command": arguments["command"],
                "command_args": list(arguments.get("args") or []),
                "project_dir": arguments.get("project_dir"),
            }
        )

    if name == "uipath_workflow_deploy":
        blocked = _gate_block_or_text(
            arguments.get("project_path"),
            "uipath_workflow_deploy",
            bool(arguments.get("allow_unverified", False)),
        )
        if blocked:
            return blocked
        blocked = _plan_gate_block_or_text(
            arguments.get("project_path"), "uipath_workflow_deploy"
        )
        if blocked:
            return blocked
        result = _deploy(
            project_path=arguments["project_path"],
            orchestrator_url=arguments["orchestrator_url"],
            tenant_name=arguments["tenant_name"],
            folder_path=arguments.get("folder_path", "Shared"),
            account_name=arguments.get("account_name"),
            process_name=arguments.get("process_name"),
            create_process=bool(arguments.get("create_process", True)),
            environment=arguments.get("environment"),
            project_type=arguments.get("project_type", "process"),
        )
        return json.dumps(result, indent=2, default=str)

    if name == "uipath_workflow_publish":
        blocked = _gate_block_or_text(
            arguments.get("project_dir"),
            "uipath_workflow_publish",
            bool(arguments.get("allow_unverified", False)),
        )
        if blocked:
            return blocked
        blocked = _plan_gate_block_or_text(
            arguments.get("project_dir"), "uipath_workflow_publish"
        )
        if blocked:
            return blocked
        result = _publish_project(
            project_dir=arguments["project_dir"],
            project_type=arguments.get("project_type", "process"),
        )
        return json.dumps(result, indent=2, default=str)

    if name == "uipath_workflow_session_status":
        pd = arguments.get("project_dir")
        if pd:
            try:
                session_gate.detect_out_of_band_changes(str(pd))
            except Exception:
                pass
            state = session_gate.status(str(pd))
            data = {
                "project_dir": session_gate._normalize(str(pd)),
                "gate_enabled": session_gate._gate_enabled(),
                **session_gate.state_to_dict(state),
            }
            return json.dumps(data, indent=2, default=str)
        for tracked_key in list(session_gate._STATES.keys()):
            try:
                session_gate.detect_out_of_band_changes(tracked_key)
            except Exception:
                continue
        snapshot = {
            "gate_enabled": session_gate._gate_enabled(),
            "projects": {
                key: session_gate.state_to_dict(state)
                for key, state in session_gate._STATES.items()
            },
        }
        return json.dumps(snapshot, indent=2, default=str)

    raise ValueError(f"Unknown workflow tool: {name}")
