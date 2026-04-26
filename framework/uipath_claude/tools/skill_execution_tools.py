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
from uipath_claude.tools.knowledge_tools import get_knowledge_tools
from uipath_claude.tools.library_tools import get_library_tools
from uipath_claude.tools.xaml_tools import get_xaml_tools
from uipath_claude.tools.uipath.askai import query_uipath_documentation
from uipath_claude.tools.uipath.cli_runner import (
    _find_uip_cli,
    _parse_first_json_payload,
    run_uip_rpa_analyze,
    run_uip_rpa_get_errors,
)

try:
    from uipath_claude.audit import append_event as _audit_append, sha256_file as _audit_sha
except Exception:  # pragma: no cover - audit must never break tools
    def _audit_append(*_a, **_kw):  # type: ignore[no-redef]
        return None

    def _audit_sha(_p):  # type: ignore[no-redef]
        return None


def _project_dir_for_audit(path_or_dest: Path) -> Path | None:
    """Walk upward from a path until a project.json is found; None otherwise."""
    p = path_or_dest if path_or_dest.is_dir() else path_or_dest.parent
    for candidate in [p, *p.parents]:
        try:
            if (candidate / "project.json").exists():
                return candidate
        except OSError:
            continue
    return None


# Maximum file size to read (50KB)
MAX_FILE_SIZE = 50 * 1024
_ANALYZER_PROFILE = (
    Path(__file__).resolve().parents[3]
    / "config"
    / "uipath"
    / "workflow-analyzer-profile.json"
)


def _get_output_root() -> Path:
    """Get the output root directory for generated files."""
    default = Path.cwd() / "generated" / "chat"
    return Path(os.environ.get("UIPATH_CHAT_OUTPUT_DIR", str(default)))


def _resolve_project_path(project_dir: str) -> Path:
    """Resolve project directory.

    Order of precedence:
    1. Absolute path passed in — use it as-is.
    2. CWD has project.json at ``cwd/project_dir`` — use that (test fixtures).
    3. ``project_dir`` is "." or "" and CWD has project.json — use CWD.
    4. ``UIPATH_PROJECT_DIR`` env var is set — use it (the user's real project).
    5. Session output dir ``generated/chat/<session_id>/`` — generated artifacts.
    """
    path = Path(project_dir)
    if path.is_absolute():
        return path

    cwd_path = Path.cwd() / project_dir
    if (cwd_path / "project.json").exists():
        return cwd_path

    if project_dir in (".", "") and (Path.cwd() / "project.json").exists():
        return Path.cwd()

    env_project_dir = os.environ.get("UIPATH_PROJECT_DIR", "").strip()
    if env_project_dir:
        env_root = Path(env_project_dir).expanduser()
        if project_dir in (".", ""):
            return env_root
        return env_root / project_dir

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

    cwd_path = Path.cwd() / file_path
    if cwd_path.exists():
        return cwd_path

    if (Path.cwd() / "project.json").exists():
        return cwd_path

    resolved = resolve_write_destination(file_path)
    if resolved is not None and resolved.exists():
        return resolved

    env_project_dir = os.environ.get("UIPATH_PROJECT_DIR", "").strip()
    if env_project_dir:
        env_candidate = Path(env_project_dir).expanduser() / file_path
        if env_candidate.exists():
            return env_candidate

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


def _candidate_write_bases() -> list[Path]:
    """Allowed roots for resolving write destinations.

    Order matters: earlier entries win when a relative path matches multiple
    bases. We prefer the current working directory when it is itself a
    UiPath project, then any explicit session output dir, then the chat
    output root.
    """
    bases: list[Path] = []
    cwd = Path.cwd()
    if (cwd / "project.json").exists():
        bases.append(cwd)
    env_project_dir = os.environ.get("UIPATH_PROJECT_DIR", "").strip()
    if env_project_dir:
        env_root = Path(env_project_dir).expanduser()
        if (env_root / "project.json").exists() or env_root.exists():
            bases.append(env_root)
    output_root = _get_output_root()
    session_id = os.environ.get("UIPATH_CHAT_SESSION_ID", "")
    if session_id:
        bases.append(output_root / session_id)
    bases.append(output_root)
    bases.append(cwd)
    seen: set[str] = set()
    unique: list[Path] = []
    for base in bases:
        try:
            key = str(base.resolve())
        except OSError:
            key = str(base)
        if key in seen:
            continue
        seen.add(key)
        unique.append(base)
    return unique


def _has_project_json_ancestor(path: Path, max_depth: int = 12) -> bool:
    """True when ``path`` (or any ancestor up to ``max_depth``) contains project.json."""
    cur = path if path.is_dir() else path.parent
    for _ in range(max_depth):
        try:
            if (cur / "project.json").exists():
                return True
        except OSError:
            return False
        if cur.parent == cur:
            return False
        cur = cur.parent
    return False


def resolve_write_destination(file_path: str) -> Path | None:
    """Resolve ``file_path`` to the actual destination on disk.

    Accepts:

    - Absolute paths under any candidate base (CWD project, session dir,
      chat output root) OR any path with a ``project.json`` ancestor.
    - Relative paths resolved against the candidate bases. The first base
      whose resulting path either already exists or whose resolved
      destination has a ``project.json`` ancestor wins. When no candidate
      satisfies that, the first base is used as a last resort.

    Returns the resolved destination, or ``None`` for paths that escape
    every allowed root and have no ``project.json`` ancestor (these are
    rejected as unsafe).
    """
    if not file_path or not file_path.strip():
        return None
    raw = file_path.strip()
    path = Path(raw)
    if path.is_absolute():
        try:
            absolute = path.resolve()
        except OSError:
            absolute = path
        for base in _candidate_write_bases():
            try:
                absolute.relative_to(base.resolve())
                return absolute
            except (OSError, ValueError):
                continue
        if _has_project_json_ancestor(absolute):
            return absolute
        return None

    normalised = raw.replace("\\", "/")
    if normalised.startswith("/"):
        return None
    if ".." in Path(normalised).parts:
        return None

    fallback: Path | None = None
    for base in _candidate_write_bases():
        candidate = (base / normalised).resolve()
        try:
            candidate.relative_to(base.resolve())
        except (OSError, ValueError):
            continue
        if fallback is None:
            fallback = candidate
        if candidate.exists() or _has_project_json_ancestor(candidate):
            return candidate
    return fallback


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


_SCAFFOLD_FILE_NAMES = frozenset({"project.json", "project.uiproj"})


def _is_scaffold_file(file_path: str) -> bool:
    """True if ``file_path`` targets a generated UiPath scaffold file."""
    name = Path(file_path).name.lower()
    return name in _SCAFFOLD_FILE_NAMES


_CODED_WORKFLOW_PATTERN = re.compile(r":\s*CodedWorkflow\b")


def _project_root_from_dest(dest: Path) -> Path | None:
    """Walk up from dest to find the project root (folder with project.json)."""
    cur = dest.parent
    for _ in range(10):
        if (cur / "project.json").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def _is_first_coded_workflow_in_xaml_project(dest: Path, content: str) -> bool:
    """Return True if writing this .cs CodedWorkflow would be the first
    coded workflow in an otherwise XAML-only project.

    Activities-first policy: a XAML project should only acquire a coded
    workflow when there is an explicit justification. This check is the
    enforcement hook used by ``write_file``.
    """
    if dest.suffix.lower() != ".cs":
        return False
    if not _CODED_WORKFLOW_PATTERN.search(content):
        return False
    project_root = _project_root_from_dest(dest)
    if project_root is None:
        return False
    for existing in project_root.rglob("*.cs"):
        if any(part.startswith(".") for part in existing.relative_to(project_root).parts):
            continue
        try:
            if existing.resolve() == dest.resolve():
                continue
        except OSError:
            continue
        try:
            existing_text = existing.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _CODED_WORKFLOW_PATTERN.search(existing_text):
            return False
    return True


@tool
def write_file(
    file_path: str,
    content: str,
    allow_scaffold_overwrite: bool = False,
    justification: str | None = None,
) -> str:
    """Write content to a file.
    
    Use this to create or update non-XAML files, .cs files, docs, etc.
    Parent directories will be created if they don't exist.
    
    IMPORTANT: Direct raw .xaml writes are blocked. Create or modify XAML via
    XML-aware XAML tools (``get_xaml_tools``) or template-scaffolded project
    generation, not by passing raw XAML text to this generic writer.

    SCAFFOLD GUARD: This tool refuses to overwrite ``project.json`` /
    ``project.uiproj`` unless ``allow_scaffold_overwrite=True`` is passed
    explicitly. To create a new project use ``create_project`` (wraps
    ``uip rpa create-project``); to add or change packages use
    ``install_package`` (wraps ``uip rpa install-or-update-packages``).
    Hand-pinning legacy package versions causes Studio dependency mismatches
    (e.g. ``UiPath.Core.Activities`` 22.x next to ``UiPath.System.Activities``
    26.x). Always run ``environment_probe`` first to learn the local Studio's
    actual installed package versions before touching scaffold files.

    ACTIVITIES-FIRST GUARD: this tool soft-blocks writing the FIRST
    ``CodedWorkflow`` ``.cs`` file into an otherwise-XAML project unless a
    ``justification`` is provided. UiPath best practice — and the planner
    skill at ``skills/skills/uipath-planner/SKILL.md`` — is to default to
    XAML/activities and only fall back to coded for the reasons listed in
    ``skills/skills/uipath-rpa/references/coded-vs-xaml-guide.md``. Pass a
    one-line ``justification`` citing the relevant rule when a coded
    workflow is genuinely the right call; the justification is logged into
    ``BUILD_LOG.md`` so reviewers can see why.

    Args:
        file_path: Relative path for the file (relative to session output dir)
        content: File content to write
        allow_scaffold_overwrite: Set True only when the user explicitly asks
            to overwrite ``project.json`` / ``project.uiproj``. Default False.
        justification: When writing the first coded workflow into a XAML
            project, a brief reason (citing the coded-vs-xaml-guide rule
            number or quoting the user's explicit request) that unblocks
            the activities-first guard and is recorded in BUILD_LOG.md.
    
    Returns:
        Success message with absolute path, or error message
    """
    if _is_scaffold_file(file_path) and not allow_scaffold_overwrite:
        return _tool(
            False,
            (
                f"Refusing to write '{Path(file_path).name}' directly. "
                "Use create_project (wraps `uip rpa create-project`) for new "
                "projects so dependencies match the local Studio install. "
                "Use install_package (wraps `uip rpa install-or-update-packages`) "
                "to add or change packages. Run environment_probe first to see "
                "the actual installed package versions. "
                "If you truly need to overwrite this scaffold file, re-call "
                "write_file with allow_scaffold_overwrite=True."
            ),
        )

    dest = resolve_write_destination(file_path)
    if dest is None:
        return _tool(False, f"Error: Invalid file path: {file_path}")

    if dest.suffix.lower() == ".xaml":
        return _tool(
            False,
            (
                "Direct raw .xaml writes are blocked. Use the XML-aware XAML "
                "tool family returned by get_xaml_tools(), or create the "
                "project from a UiPath template and extend it through "
                "structured XAML operations. Generic write_file is limited to "
                "non-XAML files so workflow XML is never synthesized or "
                "mutated as plain text."
            ),
        )

    just_text = (justification or "").strip()
    activities_first_block = _is_first_coded_workflow_in_xaml_project(dest, content)
    if activities_first_block and not just_text:
        return _tool(
            False,
            (
                "Activities-first policy: this would be the FIRST coded "
                f"(`CodedWorkflow`) workflow in '{dest.parent.name}', a XAML "
                "project. UiPath best practice (and the planner skill at "
                "skills/skills/uipath-planner/SKILL.md) is to default to "
                "XAML/activities and only fall back to coded for the reasons "
                "listed in skills/skills/uipath-rpa/references/"
                "coded-vs-xaml-guide.md. Either: "
                "(a) write a `.xaml` workflow instead, or "
                "(b) re-call write_file with a one-line `justification` "
                "citing the rule number you are satisfying (e.g. "
                "justification=\"rule 3: SDK call with no equivalent activity\")."
            ),
        )

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        proj = _project_dir_for_audit(dest)
        if proj is not None:
            try:
                rel = str(dest.resolve().relative_to(proj.resolve()))
            except ValueError:
                rel = str(dest)
            audit_event: dict[str, Any] = {
                "actor": "agent",
                "action": "write_file",
                "outcome": "pass",
                "files_written": [
                    {
                        "path": rel,
                        "sha256": _audit_sha(dest),
                        "bytes": len(content.encode("utf-8")),
                    }
                ],
            }
            if activities_first_block and just_text:
                audit_event["notes"] = (
                    f"activities-first override: justification={just_text!r}"
                )
            elif just_text:
                audit_event["notes"] = f"justification={just_text!r}"
            _audit_append(proj, audit_event)
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
        hint = ""
        if dir_path in (".", "") and not os.environ.get("UIPATH_PROJECT_DIR", "").strip():
            hint = (
                "\nIf you meant the user's UiPath project folder, this chat session "
                "has no UIPATH_PROJECT_DIR — restart with "
                "`uipath-claude chat --project-dir <abs path>` (or export the env var)."
            )
        return _tool(
            True,
            f"directory_missing=true path={dir_path} entries=[]\n"
            f"(The directory does not exist yet. If you need it, the execution "
            f"agent will create it via write_file or ensure_project_structure. "
            f"Do NOT try to create it yourself — you are read-only.)"
            f"{hint}",
        )
    
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
            "expressionLanguage": data.get("expressionLanguage", "CSharp"),
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

    pkg_label = f"{package_id}" + (f"@{version}" if version else "")
    outcome = "pass" if proc.returncode == 0 else "needs_llm_fix"
    _audit_append(
        path,
        {
            "actor": "agent",
            "action": "install_package",
            "command": cmd,
            "exit_code": proc.returncode,
            "stdout_excerpt": proc.stdout,
            "stderr_excerpt": proc.stderr,
            "outcome": outcome,
            "notes": f"package={pkg_label}",
        },
    )

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
    
    # Two-pass error-only validation. The Studio IPC behind get-errors is stateful
    # and a single call right after a write can return a stale "No diagnostics
    # found" while the next pass surfaces the real C# compile errors.
    result = run_uip_rpa_get_errors(
        str(path.resolve()),
        file_path=file_path,
        use_studio=True,
        min_severity="error",
        passes=2,
    )
    passes_run = result.get("passes_run", 0)

    if result["success"]:
        msg = f"Validation passed: 0 errors (passes_run={passes_run})"
        if result["warnings"]:
            msg += f", {len(result['warnings'])} warning(s)"
            for w in result["warnings"][:5]:
                msg += f"\n  - {w}"
        return _tool(True, msg)

    msg = f"Validation failed: {len(result['errors'])} error(s) (passes_run={passes_run})"
    for e in result["errors"][:10]:
        msg += f"\n  - {e}"
    if result["warnings"]:
        msg += f"\n{len(result['warnings'])} warning(s):"
        for w in result["warnings"][:5]:
            msg += f"\n  - {w}"

    if result.get("studio_required"):
        msg += "\n\nNote: Full validation requires UiPath Studio to be running."

    return _tool(False, msg)


def _effective_uipath_project_root(project_dir: str | None) -> Path | None:
    """Resolve a UiPath project folder for cwd / CLI injection.

    Uses the explicit ``project_dir`` argument when provided; otherwise
    ``UIPATH_PROJECT_DIR`` (e.g. from ``uipath-claude chat --project-dir``).
    """
    if project_dir and str(project_dir).strip():
        p = _resolve_project_path(str(project_dir))
    else:
        env = os.environ.get("UIPATH_PROJECT_DIR", "").strip()
        if not env:
            return None
        p = Path(env).expanduser().resolve()
    if not p.exists():
        return None
    return p


def _inject_uip_rpa_project_flags(command_args: list[str], root: Path) -> list[str]:
    """Insert ``--project-path`` / ``--project-dir`` when the agent omitted them."""
    if not command_args:
        return command_args
    verb = command_args[0]
    rest = list(command_args[1:])
    joined_lower = " ".join(a.lower() for a in command_args)

    if verb == "analyze":
        if "--project-path" in joined_lower:
            return command_args
        return ["analyze", "--project-path", str(root.resolve()), *rest]

    if verb in (
        "get-errors",
        "restore",
        "pack",
        "publish",
        "run",
        "build",
        "validate",
        "get-project-info",
        "list-workflows",
    ):
        if "--project-dir" in joined_lower or "--project-path" in joined_lower:
            return command_args
        return [verb, "--project-dir", str(root.resolve()), *rest]

    return command_args


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
    - uip rpa close-project --output json  (after open-project / Studio debug; releases DB lock)
    
    Args:
        command: The uip subcommand (e.g., "rpa", "is")
        command_args: Arguments after the subcommand (e.g. ``["find-activities", "--query", "X"]``)
        project_dir: Optional project directory for context (may be omitted when
            ``UIPATH_PROJECT_DIR`` is set, e.g. from ``uipath-claude chat --project-dir``)
    
    Returns:
        Command output or error message
    """
    # Internal MCP tools are sometimes hallucinated onto the uip CLI. Fail fast
    # with a redirect so the agent doesn't shell out and misinterpret help output.
    _MCP_ONLY_VERBS = frozenset({
        "design-propose",
        "design-approve",
        "design-reject",
        "design-status",
    })
    if command_args and command_args[0] in _MCP_ONLY_VERBS:
        bad_verb = command_args[0]
        mcp_name = "uipath_" + bad_verb.replace("-", "_")
        return _tool(
            False,
            (
                f"Error: '{bad_verb}' is not a uip CLI subcommand. "
                f"Call the MCP tool '{mcp_name}' directly. "
                "See docs/CURSOR_USER_GUIDE.md#mcp-tools-advanced."
            ),
        )

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

    root = _effective_uipath_project_root(project_dir)
    if command == "rpa" and root is not None:
        command_args = _inject_uip_rpa_project_flags(command_args, root)

    cmd = [uip_cli, command] + command_args

    cwd = None
    if root is not None:
        cwd = str(root.resolve())
    
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
    studio_hint = ""
    if (
        not ok
        and "already opened in another Studio instance" in output
    ):
        studio_hint = (
            "\n\nHint: Run `uip rpa close-project --project-dir <root>` (or close Studio "
            "windows) for every instance holding this project, then retry. While Studio "
            "holds the project database, `uip rpa analyze` cannot run. Alternatively use "
            "`uipcli package analyze` from CI without Studio.\n"
        )
    return _tool(ok, note + studio_hint + tail if (note or studio_hint) else tail)


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


def _format_build_verify_text(payload: dict) -> str:
    """Render the structured ``build_and_verify_workflow`` payload as text."""
    lines: list[str] = []
    phase = payload.get("phase", "validate")
    attempts = payload.get("attempts", 1)
    verdict = payload.get("verdict", "needs_llm_fix")
    lines.append(
        f"BUILD+VERIFY phase={phase} attempt={attempts} "
        f"verdict={verdict} success={payload.get('success', False)}"
    )

    next_action = payload.get("next_action") or "none"
    if next_action != "none":
        lines.append(f"next_action: {next_action}")

    auto_installed = payload.get("auto_installed_packages") or []
    if auto_installed:
        lines.append(f"auto_installed: {', '.join(auto_installed)}")

    errors = payload.get("errors") or []
    if errors:
        lines.append("")
        lines.append(
            f"ERRORS ({len(errors)}, fix the FIRST one then re-call build_and_verify_workflow):"
        )
        for i, err in enumerate(errors[:5], 1):
            lines.append(f"  {i}. {err}")

    warnings = payload.get("warnings") or []
    if warnings:
        lines.append("")
        lines.append(f"WARNINGS ({len(warnings)}):")
        for w in warnings[:5]:
            lines.append(f"  - {w}")

    headless = payload.get("headless_log") or ""
    if headless:
        lines.append("")
        lines.append("HEADLESS RUN LOG:")
        lines.append(headless[:1500])

    studio = payload.get("studio_debug_log") or ""
    if studio:
        lines.append("")
        lines.append("STUDIO DEBUG LOG:")
        lines.append(studio[:1500])

    skipped = payload.get("studio_debug_skipped_reason") or ""
    if skipped and not studio:
        lines.append("")
        lines.append(f"STUDIO DEBUG: skipped ({skipped})")

    log = payload.get("log_excerpt") or ""
    if log and log not in (headless, studio):
        lines.append("")
        lines.append("LOG EXCERPT:")
        lines.append(log[:1500])

    if not payload.get("success"):
        lines.append("")
        lines.append(
            "INSTRUCTIONS: Apply ONE fix (typically write_file or install_package), "
            "then call build_and_verify_workflow again. Do NOT report the task complete "
            "until this tool returns success=true."
        )

    return "\n".join(lines)


def _probe_environment(project_dir: str | None) -> dict:
    """Best-effort probe of the local UiPath Studio environment.

    Returns a dict with ``studio_instances`` (list) and ``installed_packages``
    (dict mapping package id -> version) when discoverable, plus an ``errors``
    list capturing any CLI failures so callers can decide what to do.
    """
    info: dict = {
        "studio_instances": [],
        "installed_packages": {},
        "target_framework": None,
        "errors": [],
    }

    try:
        uip_cli = _find_uip_cli()
    except Exception as exc:  # pragma: no cover - defensive
        info["errors"].append(f"uip CLI not found: {exc}")
        return info

    try:
        proc = subprocess.run(
            [uip_cli, "rpa", "list-instances", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        out = proc.stdout or proc.stderr or ""
        parsed = _parse_first_json_payload(out) or {}
        data = parsed.get("Data") if isinstance(parsed, dict) else None
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    info["studio_instances"].append(
                        {
                            "ProjectDirectory": entry.get("ProjectDirectory"),
                            "StudioVersion": entry.get("StudioVersion")
                            or entry.get("Version"),
                            "ProcessId": entry.get("ProcessId"),
                        }
                    )
    except FileNotFoundError:
        info["errors"].append("uip CLI not found on PATH")
        return info
    except subprocess.TimeoutExpired:
        info["errors"].append("list-instances timed out")
    except Exception as exc:  # pragma: no cover - defensive
        info["errors"].append(f"list-instances error: {exc}")

    if project_dir:
        try:
            path = _resolve_project_path(project_dir)
        except Exception:
            path = None
        if path is not None and (path / "project.json").exists():
            try:
                data = json.loads((path / "project.json").read_text(encoding="utf-8"))
                deps = data.get("dependencies") or {}
                if isinstance(deps, dict):
                    info["installed_packages"] = {
                        str(k): str(v) for k, v in deps.items()
                    }
                tf = data.get("targetFramework")
                if tf:
                    info["target_framework"] = tf
            except Exception as exc:
                info["errors"].append(f"project.json read error: {exc}")

            try:
                proc = subprocess.run(
                    [
                        uip_cli,
                        "rpa",
                        "list-packages",
                        "--project-dir",
                        str(path.resolve()),
                        "--output",
                        "json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                out = proc.stdout or proc.stderr or ""
                parsed = _parse_first_json_payload(out) or {}
                data = parsed.get("Data") if isinstance(parsed, dict) else None
                if isinstance(data, list):
                    for entry in data:
                        if not isinstance(entry, dict):
                            continue
                        pkg_id = entry.get("Id") or entry.get("PackageId") or entry.get("Name")
                        ver = entry.get("Version") or entry.get("ResolvedVersion")
                        if pkg_id and ver:
                            info["installed_packages"][str(pkg_id)] = str(ver)
            except subprocess.TimeoutExpired:
                info["errors"].append("list-packages timed out")
            except Exception as exc:  # pragma: no cover - defensive
                info["errors"].append(f"list-packages error: {exc}")

    return info


def _detect_dependency_mismatches(probe: dict) -> list[str]:
    """Heuristic check for common Studio/dependency mismatches.

    Today this catches the major case from the InvoiceQueueProcessor
    incident: pinning legacy ``UiPath.Core.Activities`` (22.x line) alongside
    modern ``UiPath.System.Activities`` (>= 25.x).
    """
    mismatches: list[str] = []
    pkgs = probe.get("installed_packages") or {}
    if not isinstance(pkgs, dict):
        return mismatches

    def _major(v: str) -> int | None:
        m = re.match(r"\[?\s*(\d+)", v or "")
        return int(m.group(1)) if m else None

    sys_ver = pkgs.get("UiPath.System.Activities")
    core_ver = pkgs.get("UiPath.Core.Activities")
    sys_major = _major(sys_ver) if sys_ver else None
    core_major = _major(core_ver) if core_ver else None
    if sys_major and core_major and sys_major >= 25 and core_major < 25:
        mismatches.append(
            f"UiPath.Core.Activities pinned to {core_ver} (legacy {core_major}.x) "
            f"but UiPath.System.Activities is {sys_ver} ({sys_major}.x). "
            "Modern Studio installs do not ship the legacy 22.x Core.Activities line. "
            "Remove UiPath.Core.Activities (or use install_package with a matching "
            "version) and let create_project pick defaults that match local Studio."
        )

    return mismatches


@tool
def environment_probe(project_dir: str | None = None) -> str:
    """Probe local UiPath Studio environment and installed packages.

    READ-ONLY. Run this BEFORE choosing activity packages or creating /
    editing ``project.json`` so the agent picks versions that match the
    local Studio install (avoids 4-major-version dependency mismatches that
    Studio silently auto-resolves).

    Reports:
    - Open Studio instance(s) discovered via ``uip rpa list-instances``.
    - For an existing project: installed package versions via
      ``uip rpa list-packages`` and the targetFramework declared in
      ``project.json``.
    - Any detected dependency mismatches (e.g. legacy
      ``UiPath.Core.Activities`` next to modern ``UiPath.System.Activities``).

    Args:
        project_dir: Optional project directory (defaults to no project,
            so only Studio instances are reported).

    Returns:
        JSON-shaped text with ``studio_instances``, ``installed_packages``,
        ``target_framework``, ``mismatches``, and ``errors`` from CLI calls.
    """
    info = _probe_environment(project_dir)
    info["mismatches"] = _detect_dependency_mismatches(info)
    info["success"] = not info["errors"]

    summary_lines = [
        f"Studio instances: {len(info['studio_instances'])}",
        f"Installed packages: {len(info['installed_packages'])}",
    ]
    if info.get("target_framework"):
        summary_lines.append(f"targetFramework: {info['target_framework']}")
    if info["mismatches"]:
        summary_lines.append("")
        summary_lines.append("DEPENDENCY MISMATCHES (fix before continuing):")
        for m in info["mismatches"]:
            summary_lines.append(f"  - {m}")
    if info["errors"]:
        summary_lines.append("")
        summary_lines.append("CLI errors (probe is best-effort):")
        for e in info["errors"]:
            summary_lines.append(f"  - {e}")

    summary_lines.append("")
    summary_lines.append("Raw:")
    summary_lines.append(json.dumps(info, indent=2, default=str)[:3000])

    ok = not info["mismatches"] and not info["errors"]
    return _tool(ok, "\n".join(summary_lines))


_TEMPLATE_ID_BY_TYPE = {
    "process": "BlankTemplate",
    "library": "LibraryProcessTemplate",
    "coded": "BlankTemplate",
    "test": "TestAutomationProjectTemplate",
}

_STUDIO_UNRESOLVABLE_MARKERS = (
    "could not resolve studio installation directory",
    "studio installation directory",
    "use --studio-dir",
)


def _resolve_studio_dir() -> str | None:
    """Return the first existing Studio installation directory.

    Resolution order:
      1. ``UIPATH_STUDIO_DIR`` env var
      2. ``C:\\Program Files\\UiPath\\Studio``
      3. ``C:\\Program Files (x86)\\UiPath\\Studio``
      4. ``%LOCALAPPDATA%\\UiPath\\Studio``
      5. ``%LOCALAPPDATA%\\Programs\\UiPath\\Studio``

    Returns ``None`` on non-Windows or when none of the above exist.
    """
    env = os.environ.get("UIPATH_STUDIO_DIR")
    if env and Path(env).exists():
        return env

    if os.name != "nt":
        return None

    candidates = [
        r"C:\Program Files\UiPath\Studio",
        r"C:\Program Files (x86)\UiPath\Studio",
    ]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(str(Path(local) / "UiPath" / "Studio"))
        candidates.append(str(Path(local) / "Programs" / "UiPath" / "Studio"))

    for c in candidates:
        if Path(c).exists():
            return c
    return None


def _minimal_main_xaml_for_scaffold() -> str:
    """Minimal Sequence workflow used by the CLI-only fallback path."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Activity x:Class="Main"\n'
        ' xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"\n'
        ' xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n'
        '  <Sequence DisplayName="Main Sequence">\n'
        '    <WriteLine Text="Generated scaffold (CLI fallback) - replace in Studio." />\n'
        '  </Sequence>\n'
        '</Activity>\n'
    )


def _cli_fallback_scaffold(target: Path, project_name: str, project_type: str) -> str:
    """Hand-build a minimal project.json + Main.xaml when Studio IPC is unavailable.

    Writes empty ``dependencies`` so ``install_package`` (which wraps
    ``uip rpa install-or-update-packages``) can populate them later from the
    real Studio install when one becomes available.
    """
    target.mkdir(parents=True, exist_ok=True)
    proj_type_camel = "Library" if project_type == "library" else "Process"
    expression_language = "CSharp"
    project_json = {
        "name": project_name,
        "projectId": "",
        "description": f"{project_name} (CLI-fallback scaffold)",
        "main": "Main.xaml",
        "dependencies": {},
        "webServices": [],
        "entitiesStores": [],
        "schemaVersion": "4.0",
        "studioVersion": "0.0.0.0",
        "projectVersion": "1.0.0",
        "runtimeOptions": {"autoDispose": False, "isAttended": False},
        "designOptions": {"projectProfile": "Development"},
        "expressionLanguage": expression_language,
        "entryPoints": [
            {"filePath": "Main.xaml", "uniqueId": "00000000-0000-0000-0000-000000000000", "input": [], "output": []}
        ],
        "isTemplate": False,
        "templateProjectData": {},
        "publishData": {},
        "targetFramework": "Windows",
        "projectType": proj_type_camel,
    }
    (target / "project.json").write_text(
        json.dumps(project_json, indent=2), encoding="utf-8"
    )
    (target / "Main.xaml").write_text(_minimal_main_xaml_for_scaffold(), encoding="utf-8")
    return str(target / "project.json")


def _looks_like_studio_unresolvable(output: str) -> bool:
    if not output:
        return False
    low = output.lower()
    return any(marker in low for marker in _STUDIO_UNRESOLVABLE_MARKERS)


@tool
def create_project(
    project_dir: str,
    project_name: str,
    project_type: str = "process",
    auto_verify: bool = True,
) -> str:
    """Create a UiPath project via ``uip rpa create-project`` and verify it.

    Use this INSTEAD of writing ``project.json`` by hand. The CLI generates
    a ``project.json`` whose dependencies match the local Studio install,
    avoiding the legacy-vs-modern dependency mismatches that occur when an
    LLM hand-pins package versions.

    Strategy (uip 0.1.21+):
      1. Try ``uip rpa [--studio-dir <auto>] create-project --template-id <tpl>``
         where ``<tpl>`` is mapped from ``project_type``:
           - ``process`` -> ``BlankTemplate``
           - ``library`` -> ``LibraryProcessTemplate``
           - ``coded``   -> ``BlankTemplate`` + ``--expression-language CSharp``
      2. If Studio IPC is unavailable (CLI reports "Could not resolve Studio
         installation directory" or returns success without writing
         ``project.json``), fall back to a CLI-only scaffold: ``uip solution
         new`` (best-effort) then write a minimal ``project.json`` + ``Main.xaml``
         with empty dependencies. The result is marked
         ``created_via: "cli-fallback"`` for diagnostics.

    Args:
        project_dir: Parent directory in which to create the project folder.
        project_name: Name of the new project (folder + project.name).
        project_type: ``process`` (default), ``library``, ``coded``, or ``test``.
        auto_verify: When True (default), call ``build_and_verify_workflow``
            on the new project (``run_after_validate=False``) and append its
            payload to the result.

    Returns:
        CLI output, the path to the generated project.json, the
        ``created_via`` marker, and (when ``auto_verify=True``) the
        verification payload.
    """
    base = _resolve_project_path(project_dir)
    base.mkdir(parents=True, exist_ok=True)

    uip_cli = _find_uip_cli()
    studio_dir = _resolve_studio_dir()
    template_id = _TEMPLATE_ID_BY_TYPE.get(project_type, "BlankTemplate")

    cmd: list[str] = [uip_cli, "rpa"]
    if studio_dir:
        cmd.extend(["--studio-dir", studio_dir])
    cmd.extend(
        [
            "create-project",
            "--name",
            project_name,
            "--location",
            str(base.resolve()),
            "--template-id",
            template_id,
            "--output",
            "json",
        ]
    )
    cmd.extend(["--expression-language", "CSharp", "--target-framework", "Windows"])

    try:
        timeout_s = int(os.environ.get("UIPATH_CREATE_PROJECT_TIMEOUT", "300"))
    except ValueError:
        timeout_s = 300

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError:
        return _tool(False, "Error: uip CLI not found. Install with: npm install -g @uipath/cli")
    except subprocess.TimeoutExpired:
        return _tool(False, f"Error: create-project timed out after {timeout_s}s")

    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    parsed = _parse_first_json_payload(output) or {}
    target = (base / project_name).resolve()
    project_json = target / "project.json"

    studio_failed = (
        _looks_like_studio_unresolvable(output)
        or (proc.returncode == 0 and not project_json.exists())
        or (proc.returncode != 0 and _looks_like_studio_unresolvable(output))
    )

    def _success_body(via: str, extra: str = "") -> str:
        head = (
            f"Created project at {target}\n"
            f"project.json: {project_json}\n"
            f"created_via: {via}\n\n"
            f"{output[:1500]}"
        )
        if extra:
            head += "\n\n--- fallback log ---\n" + extra[:1500]
        return head

    if proc.returncode == 0 and project_json.exists() and project_json.stat().st_size > 0:
        head = _success_body("studio")
        if not auto_verify:
            return _tool(True, head)
        verify_text = build_and_verify_workflow.invoke(
            {
                "project_dir": str(target),
                "max_attempts": 5,
                "run_after_validate": False,
                "require_studio_debug": False,
            }
        )
        verify_ok = isinstance(verify_text, str) and verify_text.startswith("[OK]")
        body = head + "\n\n--- auto-verify (build_and_verify_workflow) ---\n" + (
            verify_text or ""
        )
        return _tool(verify_ok, body)

    if studio_failed:
        # CLI-only fallback: best-effort uip solution new then hand-build project.json
        fb_log_parts: list[str] = []
        try:
            fb_proc = subprocess.run(
                [uip_cli, "solution", "new", project_name, "--output", "json"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                cwd=str(base.resolve()),
            )
            fb_log_parts.append(
                f"solution new exit={fb_proc.returncode}\n{(fb_proc.stdout or '') + (fb_proc.stderr or '')}"
            )
        except Exception as exc:
            fb_log_parts.append(f"solution new error: {exc}")

        try:
            _cli_fallback_scaffold(target, project_name, project_type)
        except Exception as exc:
            return _tool(
                False,
                f"create-project: Studio IPC unavailable AND CLI fallback failed: {exc}\n\n--- CLI log ---\n{output[:1500]}",
            )

        if not (project_json.exists() and project_json.stat().st_size > 0):
            return _tool(
                False,
                f"create-project: CLI fallback ran but project.json missing at {project_json}\n\n--- CLI log ---\n{output[:1500]}",
            )

        head = _success_body("cli-fallback", extra="\n".join(fb_log_parts))
        if not auto_verify:
            return _tool(True, head)
        # Skip auto_verify on fallback: it requires Studio (which is what failed).
        return _tool(True, head + "\n\n[note] auto-verify skipped: fallback path has no Studio.")

    if isinstance(parsed, dict) and parsed.get("Message"):
        return _tool(False, f"create-project failed: {parsed['Message']}\n\n{output[:1500]}")

    return _tool(False, f"create-project failed (exit {proc.returncode})\n\n{output[:1500]}")


def _project_main_entry(project_path: Path) -> str | None:
    """Read ``project.json`` and return the ``main`` workflow filename, if any."""
    pj = project_path / "project.json"
    if not pj.exists():
        return None
    try:
        data = json.loads(pj.read_text(encoding="utf-8"))
    except Exception:
        return None
    main = data.get("main")
    if isinstance(main, str) and main.lower().endswith(".xaml"):
        return main
    return None


def _discover_workflow_files(project_dir: str) -> list[str]:
    """Return relative paths of every ``.xaml`` workflow under ``project_dir``.

    Skips Studio internal folders (``.local``, ``.objects``, ``.screenshots``,
    ``.entities``, ``.tmh``) and any file under a ``Tests`` folder so we don't
    accidentally validate test scaffolding twice.
    """
    try:
        path = _resolve_project_path(project_dir)
    except Exception:
        return []
    if not path.exists():
        return []

    skip_parts = {".local", ".objects", ".screenshots", ".entities", ".tmh"}
    out: list[str] = []
    for xaml in path.rglob("*.xaml"):
        if any(part in skip_parts for part in xaml.relative_to(path).parts[:-1]):
            continue
        out.append(str(xaml.relative_to(path)).replace("\\", "/"))
    out.sort(key=lambda p: (0 if Path(p).name.lower() == "main.xaml" else 1, p.lower()))
    return out


def _attempt_auto_install(probe: dict) -> tuple[list[str], list[str]]:
    """Best-effort auto-install of missing packages flagged by the probe.

    Returns ``(installed, errors)`` lists. Only packages whose target version
    is unambiguously implied by the probe (e.g. via Studio's installed pin)
    are auto-installed. Anything ambiguous is skipped and reported as an
    error so the LLM / human can decide.
    """
    installed: list[str] = []
    errors: list[str] = []
    project_dir = probe.get("project_dir")
    if not project_dir:
        return installed, ["auto-install skipped: probe has no project_dir"]

    desired = probe.get("desired_packages") or {}
    if not isinstance(desired, dict) or not desired:
        return installed, []

    for pkg_id, version in desired.items():
        if not pkg_id or not version:
            continue
        try:
            result_text = install_package.invoke(
                {
                    "project_dir": project_dir,
                    "package_id": pkg_id,
                    "version": version,
                }
            )
        except Exception as exc:
            errors.append(f"auto-install {pkg_id}@{version} raised: {exc}")
            continue
        if isinstance(result_text, str) and result_text.startswith("[OK]"):
            installed.append(f"{pkg_id}@{version}")
        else:
            errors.append(f"auto-install {pkg_id}@{version} failed: {result_text[:200]}")
    return installed, errors


def _studio_available(probe: dict) -> bool:
    """True iff at least one running Studio instance was detected."""
    instances = probe.get("studio_instances") or []
    return bool(instances)


def _run_one_verify_attempt(
    project_dir: str,
    file_path: str | None,
    run_after_validate: bool,
    input_arguments: str | None,
    timeout_seconds: int,
    auto_install_packages: bool,
    studio_debug_after_run: bool,
    attempt_index: int,
    max_attempts: int,
    require_studio_debug: bool = True,
) -> dict:
    """One attempt of the validate -> headless run -> studio debug pipeline.

    Returns the structured payload (without the surrounding ToolOutcome
    text). The caller decides whether to loop based on ``next_action``.
    """
    payload: dict = {
        "success": False,
        "phase": "probe",
        "attempts": attempt_index,
        "iterations_run": attempt_index,
        "file_path": file_path,
        "files_checked": [],
        "errors": [],
        "warnings": [],
        "next_action": "fix_and_recall",
        "verdict": "needs_llm_fix",
        "log_excerpt": "",
        "headless_log": "",
        "studio_debug_log": "",
        "studio_debug_skipped_reason": "",
        "auto_installed_packages": [],
        "max_attempts": max_attempts,
        "analyzer_profile": str(_ANALYZER_PROFILE),
    }

    probe = _probe_environment(project_dir)
    probe.setdefault("project_dir", project_dir)
    mismatches = _detect_dependency_mismatches(probe)

    if mismatches:
        if auto_install_packages:
            installed, install_errors = _attempt_auto_install(probe)
            payload["auto_installed_packages"] = installed
            if install_errors and not installed:
                payload["phase"] = "probe"
                payload["errors"] = mismatches + install_errors
                payload["next_action"] = "install_packages"
                payload["verdict"] = "needs_human"
                payload["log_excerpt"] = json.dumps(
                    {
                        "studio_instances": probe.get("studio_instances"),
                        "installed_packages": probe.get("installed_packages"),
                    },
                    default=str,
                )[:1500]
                return payload
            probe = _probe_environment(project_dir)
            probe.setdefault("project_dir", project_dir)
            mismatches = _detect_dependency_mismatches(probe)
        if mismatches:
            payload["phase"] = "probe"
            payload["errors"] = mismatches
            payload["next_action"] = "install_packages"
            payload["verdict"] = "needs_human"
            payload["log_excerpt"] = json.dumps(
                {
                    "studio_instances": probe.get("studio_instances"),
                    "installed_packages": probe.get("installed_packages"),
                },
                default=str,
            )[:1500]
            return payload

    payload["phase"] = "validate"
    path = _resolve_project_path(project_dir)

    if file_path:
        targets = [file_path]
    else:
        targets = _discover_workflow_files(project_dir)
        if not targets:
            payload["errors"] = [
                "No .xaml workflows found under project_dir. Pass file_path "
                "explicitly or scaffold the project first via create_project."
            ]
            payload["verdict"] = "needs_human"
            return payload

    payload["files_checked"] = targets
    aggregated_warnings: list[str] = []
    failing_file: str | None = None
    val: dict | None = None

    for target in targets:
        # Verify-gate contract: two clean passes of `uip rpa get-errors --min-severity error`
        # are required to defeat the Studio IPC stale-cache failure mode that previously
        # let real C# compile errors slip through (see docs/build-logs/README.md).
        result = run_uip_rpa_get_errors(
            str(path.resolve()),
            file_path=target,
            use_studio=True,
            min_severity="error",
            passes=2,
        )
        aggregated_warnings.extend(result.get("warnings") or [])
        if not result.get("success"):
            failing_file = target
            val = result
            break
        val = result

    if failing_file is not None and val is not None:
        payload["file_path"] = failing_file
        payload["errors"] = list(val.get("errors") or [])
        payload["warnings"] = aggregated_warnings
        payload["next_action"] = "fix_and_recall"
        payload["verdict"] = "needs_llm_fix"
        if val.get("studio_required"):
            payload["log_excerpt"] = "Note: Full validation requires UiPath Studio to be running."
        return payload

    payload["warnings"] = aggregated_warnings

    payload["phase"] = "analyze"
    analyzer = run_uip_rpa_analyze(
        str(path.resolve()),
        rule_profile=str(_ANALYZER_PROFILE),
    )
    payload["warnings"].extend(analyzer.get("warnings") or [])
    if not analyzer.get("success"):
        payload["errors"] = list(analyzer.get("errors") or ["Workflow Analyzer failed"])
        payload["next_action"] = "fix_and_recall"
        payload["verdict"] = "needs_llm_fix"
        payload["log_excerpt"] = (analyzer.get("raw_output") or "")[:1500]
        return payload

    if not run_after_validate:
        if require_studio_debug:
            payload["phase"] = "studio_debug"
            payload["errors"] = [
                "Studio debug step did not run (run_after_validate=False). "
                "Verify gate refuses to mark the project verified without an "
                "attached Studio debug pass. Set run_after_validate=True with "
                "Studio running, or rerun with require_studio_debug=False "
                "after the user explicitly waives the Studio debug requirement."
            ]
            payload["next_action"] = "start_studio_or_waive"
            payload["verdict"] = "needs_human"
            payload["success"] = False
            return payload
        payload["success"] = True
        payload["phase"] = "done"
        payload["next_action"] = "none"
        payload["verdict"] = "pass"
        return payload

    entry_file = file_path or _project_main_entry(path) or "Main.xaml"
    payload["file_path"] = entry_file
    payload["phase"] = "run"
    run_kwargs: dict[str, Any] = {
        "project_dir": project_dir,
        "file_path": entry_file,
        "timeout_seconds": int(timeout_seconds),
    }
    if input_arguments is not None:
        run_kwargs["input_arguments"] = input_arguments
    run_text = run_workflow.invoke(run_kwargs)

    run_ok = isinstance(run_text, str) and run_text.startswith("[OK]")
    payload["headless_log"] = (run_text or "")[:1500]
    payload["log_excerpt"] = payload["headless_log"]

    if not run_ok:
        payload["errors"] = ["Headless runtime execution failed; see headless_log."]
        payload["next_action"] = "fix_and_recall"
        payload["verdict"] = "needs_llm_fix"
        return payload

    studio_ran = False
    if not studio_debug_after_run:
        payload["studio_debug_skipped_reason"] = "studio_debug_after_run=False"
    elif not _studio_available(probe):
        payload["studio_debug_skipped_reason"] = (
            "No running UiPath Studio instance detected; headless run only."
        )
    else:
        payload["phase"] = "studio_debug"
        try:
            studio_text = debug_workflow.invoke(
                {"project_dir": project_dir, "file_path": entry_file}
            )
        except Exception as exc:
            studio_text = f"[ERR] debug_workflow raised: {exc}"
        payload["studio_debug_log"] = (studio_text or "")[:1500]
        studio_ok = isinstance(studio_text, str) and studio_text.startswith("[OK]")
        if not studio_ok:
            payload["errors"] = [
                "Studio debug session failed; see studio_debug_log."
            ]
            payload["next_action"] = "fix_and_recall"
            payload["verdict"] = "needs_llm_fix"
            return payload
        studio_ran = True

    if require_studio_debug and not studio_ran:
        payload["errors"] = [
            "Studio debug step did not run (skipped or unavailable). Verify "
            "gate refuses to mark a project verified without an attached "
            "Studio debug pass. Start UiPath Studio against this project, or "
            "rerun with require_studio_debug=False after the user explicitly "
            "waives the Studio debug requirement."
        ]
        payload["next_action"] = "start_studio_or_waive"
        payload["verdict"] = "needs_human"
        payload["success"] = False
        return payload

    payload["success"] = True
    payload["phase"] = "done"
    payload["next_action"] = "none"
    payload["verdict"] = "pass"
    return payload


@tool
def build_and_verify_workflow(
    project_dir: str,
    file_path: str | None = None,
    max_attempts: int = 5,
    run_after_validate: bool = True,
    input_arguments: str | None = None,
    timeout_seconds: int = 60,
    auto_install_packages: bool = True,
    studio_debug_after_run: bool = True,
    require_studio_debug: bool = True,
) -> str:
    """Build, validate, headless-run, and Studio-debug a workflow in a server-side loop.

    This is the canonical "did it actually work" tool. The Cursor / Claude
    agent MUST call this after every write_file / install_package cycle and
    treat ``success=true`` as the only signal that the project is verified.
    Do NOT mark the task complete while ``verdict`` is anything other than
    ``"pass"``.

    Server-side loop (up to ``max_attempts`` iterations):
    1. Probe local Studio + installed packages (``environment_probe``). If
       a dependency mismatch is detected and ``auto_install_packages=True``
       (default), the loop calls ``install_package`` for any version
       unambiguously implied by Studio's installed pin and re-probes. If
       mismatches persist, the loop returns ``next_action="install_packages"``
       with verdict ``"needs_human"``.
    2. Run ``uip rpa get-errors`` over every ``.xaml`` (or just ``file_path``).
       On the first failure, return diagnostics with verdict ``"needs_llm_fix"``.
    3. When validation is clean and ``run_after_validate=True``: execute the
       entry workflow headless via ``run_workflow``. On failure, return with
       ``headless_log`` populated and verdict ``"needs_llm_fix"``.
    4. When the headless run succeeds AND a Studio instance is detected AND
       ``studio_debug_after_run=True`` (default): also start a Studio debug
       session via ``debug_workflow`` and capture ``studio_debug_log``. The
       overall attempt only passes when the Studio debug session also passes.
       When no Studio is running, the step is skipped and the reason is
       reported in ``studio_debug_skipped_reason``.

    Loop semantics: between iterations the tool re-runs the full pipeline;
    if the only failing step is ``probe`` and ``auto_install_packages=True``
    succeeded, the loop transparently advances. For LLM-driven fixes the
    loop returns early so the agent can patch XAML and call again.

    Args:
        project_dir: Path to the UiPath project directory.
        file_path: Workflow file to verify, e.g. ``Main.xaml``. When omitted
            (recommended), every ``.xaml`` in the project is validated;
            runtime execution still targets the project ``main`` entry.
        max_attempts: Maximum loop iterations before returning. Default 5.
        run_after_validate: When True (default), run the workflow after
            static validation passes.
        input_arguments: Optional JSON string of input args for the run step.
        timeout_seconds: Forwarded to ``run_workflow``. Default 60.
        auto_install_packages: When True (default), the loop attempts to
            resolve dependency mismatches via ``install_package`` itself
            instead of bailing out for an LLM fix.
        studio_debug_after_run: When True (default), also attach a Studio
            debug session after a successful headless run, when a Studio
            instance is detected.
        require_studio_debug: When True (default), the verify gate refuses
            to emit ``verdict="pass"`` unless an attached Studio debug pass
            also ran. If Studio is unavailable or ``studio_debug_after_run``
            is False, the call returns ``verdict="needs_human"`` with
            ``next_action="start_studio_or_waive"``. Set this to False ONLY
            when the user explicitly waives the Studio debug step.

    Returns:
        Text payload with a structured JSON block::

            {"success": bool, "phase": str, "attempts": int,
             "iterations_run": int, "file_path": str|None,
             "files_checked": [str, ...],
             "errors": [...], "warnings": [...],
             "next_action": "fix_and_recall"|"install_packages"|"none",
             "verdict": "pass"|"needs_llm_fix"|"needs_human",
             "headless_log": str, "studio_debug_log": str,
             "studio_debug_skipped_reason": str,
             "auto_installed_packages": [str, ...],
             "log_excerpt": str}
    """
    safe_max = max(1, int(max_attempts))
    payload: dict | None = None
    last_phase = "probe"

    for attempt in range(1, safe_max + 1):
        payload = _run_one_verify_attempt(
            project_dir=project_dir,
            file_path=file_path,
            run_after_validate=run_after_validate,
            input_arguments=input_arguments,
            timeout_seconds=timeout_seconds,
            auto_install_packages=auto_install_packages,
            studio_debug_after_run=studio_debug_after_run,
            attempt_index=attempt,
            max_attempts=safe_max,
            require_studio_debug=require_studio_debug,
        )
        last_phase = payload.get("phase", last_phase)

        if payload.get("success"):
            text = _format_build_verify_text(payload)
            return _tool(True, text + "\n\n" + json.dumps(payload, default=str))

        # Only advance the loop when the iteration made automatic progress
        # (e.g. auto-installed packages). Anything that needs an LLM patch or
        # human input is returned immediately so the caller can act.
        installed = payload.get("auto_installed_packages") or []
        if installed and last_phase == "probe":
            continue
        break

    assert payload is not None
    text = _format_build_verify_text(payload)

    try:
        proj_for_log = _resolve_project_path(project_dir)
        _audit_append(
            proj_for_log,
            {
                "actor": "agent",
                "action": "build_and_verify",
                "exit_code": 0 if payload.get("success") else "non-zero",
                "outcome": payload.get("verdict") or ("pass" if payload.get("success") else "needs_llm_fix"),
                "studio_attached": (
                    True if payload.get("studio_debug_log") else (
                        "skipped" if payload.get("studio_debug_skipped_reason") else "unknown"
                    )
                ),
                "notes": (
                    f"phase={payload.get('phase')} files_checked={len(payload.get('files_checked') or [])} "
                    f"errors={len(payload.get('errors') or [])} warnings={len(payload.get('warnings') or [])}"
                ),
                "stdout_excerpt": payload.get("headless_log") or "",
                "stderr_excerpt": payload.get("studio_debug_log") or "",
            },
        )
    except Exception:
        pass

    return _tool(bool(payload.get("success")), text + "\n\n" + json.dumps(payload, default=str))


@tool
def validate_and_fix_loop(
    project_dir: str,
    file_path: str,
    max_attempts: int = 5,
) -> str:
    """Single-shot static validation (delegates to build_and_verify_workflow).

    DEPRECATED NAME: kept for backward compatibility with older callers in
    ``agentic_executor``. Internally calls
    ``build_and_verify_workflow(run_after_validate=False)``.

    Prefer ``build_and_verify_workflow`` directly so you also get optional
    runtime execution and dependency-mismatch detection.

    Args:
        project_dir: Path to the UiPath project directory.
        file_path: Relative path to the file to validate.
        max_attempts: Forwarded to ``build_and_verify_workflow``.

    Returns:
        Same payload shape as ``build_and_verify_workflow``.
    """
    return build_and_verify_workflow.invoke(
        {
            "project_dir": project_dir,
            "file_path": file_path,
            "max_attempts": int(max_attempts),
            "run_after_validate": False,
        }
    )


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

    success = proc.returncode == 0
    _audit_append(
        path,
        {
            "actor": "agent",
            "action": "start_debugging",
            "command": cmd,
            "exit_code": proc.returncode,
            "stdout_excerpt": proc.stdout,
            "stderr_excerpt": proc.stderr,
            "outcome": "pass" if success else "needs_llm_fix",
            "studio_attached": True,
            "notes": f"file={file_path} command=StartDebugging",
        },
    )

    if success:
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
        _audit_append(
            path,
            {
                "actor": "agent",
                "action": "run_file",
                "command": cmd,
                "exit_code": "no-output",
                "outcome": "needs_llm_fix",
                "notes": "no output from uip rpa run-file",
            },
        )
        return _tool(False, "Error: No output from CLI command. The workflow may not have executed.")

    parsed = _parse_runtime_response(output_text, verbose)

    # 5. FORMAT RESPONSE
    result = _format_runtime_result(parsed, verbose)

    # 6. TOKEN EFFICIENCY - Truncate if too long
    if len(result) > 2000 and not verbose:
        result = result[:2000] + "\n\n... (TRUNCATED - use verbose=True for full output)"

    success = bool(parsed.get("success"))
    _audit_append(
        path,
        {
            "actor": "agent",
            "action": "run_file",
            "command": cmd,
            "exit_code": 0 if success else "non-zero",
            "stdout_excerpt": output_text,
            "outcome": "pass" if success else "needs_llm_fix",
            "notes": f"file={file_path} command=StartExecution",
        },
    )
    return _tool(success, result)


@tool
def ensure_project_structure(project_dir: str = ".") -> str:
    """Confirm a project exists at ``project_dir``, OR delegate to create_project.

    Behavior:
    - If ``project_dir/project.json`` exists, return success (no changes).
    - If it does NOT exist, this tool refuses to hand-write a minimal
      ``project.json`` and instead instructs the caller to run
      ``create_project`` so dependencies match the local Studio install.

    Hand-written scaffolds are the root cause of multi-major dependency
    mismatches (e.g. legacy ``UiPath.Core.Activities`` next to modern
    ``UiPath.System.Activities``). Always go through ``create_project``.

    Args:
        project_dir: Path to the project directory.

    Returns:
        Status message about project structure.
    """
    path = _resolve_project_path(project_dir)
    path.mkdir(parents=True, exist_ok=True)

    project_json = path / "project.json"
    if project_json.exists():
        return _tool(True, f"Project structure OK: {project_json} exists")

    return _tool(
        False,
        (
            f"No project.json at {project_json}. Refusing to hand-write a "
            "minimal project.json (causes Studio dependency mismatches). "
            "Call create_project(project_dir=<parent>, project_name=<name>) "
            "instead - it wraps `uip rpa create-project` and auto-validates "
            "the result."
        ),
    )


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
    out = query_uipath_documentation(question)
    return out.to_text()


def get_planning_tools() -> list:
    """Return the list of read-only tools available during planning."""
    return [
        read_file,
        list_directory,
        read_project_json,
        find_activity_info,
        query_uipath_docs,
    ] + get_library_tools() + get_knowledge_tools()


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

        _audit_append(
            proj_path,
            {
                "actor": "agent",
                "action": "deploy_to_orchestrator",
                "command": deploy_cmd,
                "exit_code": 0,
                "outcome": "pass",
                "notes": (
                    f"package={proj_name}@{proj_version} folder={folder_path} "
                    f"orch={orch_url} tenant={tenant}"
                ),
                "files_written": [
                    {
                        "path": pack_output.name,
                        "sha256": _audit_sha(pack_output),
                        "bytes": pack_output.stat().st_size if pack_output.exists() else 0,
                    }
                ],
            },
        )

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
    ] + get_xaml_tools() + get_library_tools() + get_knowledge_tools()
