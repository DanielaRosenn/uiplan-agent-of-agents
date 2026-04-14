"""Materialize file blocks from assistant text (deterministic writes)."""
from __future__ import annotations

import json
import os
import re
import uuid
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_get_errors

_BLOCK = re.compile(
    r"<<<UIPATH_FILE path=(?P<q>[\"'])(?P<rel>.+?)(?P=q)>>>(?P<body>.*?)<<<END_UIPATH_FILE>>>",
    re.DOTALL,
)

# First line inside fence: `path: relative/path.ext` then body until closing ```
_FENCE_PATH = re.compile(
    r"```[^\n`]*\npath:\s*(?P<rel>[^\n]+)\n(?P<body>.*?)```",
    re.DOTALL,
)
_MAIL_DEPENDENCY_NAME = "UiPath.Mail.Activities"
_MAIL_DEPENDENCY_VERSION = "[2.5.10]"
_IS_DEPENDENCY_NAME = "UiPath.IntegrationService.Activities"
_IS_DEPENDENCY_VERSION = "[1.14.2]"
_DEPENDENCY_HINTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        _MAIL_DEPENDENCY_NAME,
        _MAIL_DEPENDENCY_VERSION,
        (
            "ui:GetOutlookMailMessages",
            "ui:SendOutlookMailMessage",
            "ui:SaveMailMessage",
            "ui:StartOutlook",
            "ui:GetOutlookNamespace",
            "ui:GetOutlookFolder",
            "ui:ForEachOutlookMessageFile",
            "snm:MailMessage",
            "System.Net.Mail",
            "outlook:MailItem",
            "Microsoft.Office.Interop.Outlook",
        ),
    ),
    (
        _IS_DEPENDENCY_NAME,
        _IS_DEPENDENCY_VERSION,
        (
            "xmlns:uip=",
            "uip:",
            "UiPath.IntegrationService.Activities",
        ),
    ),
)


def _safe_join(root: Path, rel: str) -> Path | None:
    rel = rel.strip().replace("\\", "/")
    if not rel or rel.startswith("/"):
        return None
    if Path(rel).is_absolute():
        return None
    parts = Path(rel).parts
    if ".." in parts:
        return None
    dest = (root / rel).resolve()
    try:
        dest.relative_to(root.resolve())
    except ValueError:
        return None
    return dest


def _write_under_root(root: Path, rel: str, body: str) -> Path | None:
    dest = _safe_join(root, rel)
    if dest is None:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    return dest


def _is_blocked_project_file(rel: str) -> bool:
    """Return True for project scaffold files that chat should not write by default."""
    filename = Path(rel.replace("\\", "/")).name.lower()
    return filename in {"project.json", "project.uiproj"}


def _detect_required_dependencies(xaml_content: str) -> set[str]:
    """Detect dependency package ids required by XAML content."""
    required: set[str] = set()
    for package_id, _, hints in _DEPENDENCY_HINTS:
        if any(hint in xaml_content for hint in hints):
            required.add(package_id)
    return required


def _ensure_project_dependency(
    output_root: Path, dependency_name: str, dependency_version: str
) -> None:
    """Ensure project.json contains a specific dependency."""
    project_json_path = output_root / "project.json"
    if not project_json_path.exists() and not ensure_project_json(output_root):
        return
    try:
        project_data = json.loads(project_json_path.read_text(encoding="utf-8"))
    except Exception:
        return
    dependencies = project_data.get("dependencies")
    if not isinstance(dependencies, dict):
        dependencies = {}
        project_data["dependencies"] = dependencies
    if dependency_name in dependencies:
        return
    dependencies[dependency_name] = dependency_version
    try:
        project_json_path.write_text(
            json.dumps(project_data, indent=2),
            encoding="utf-8",
        )
    except Exception:
        return


def contains_file_blocks(text: str) -> bool:
    """Check whether assistant text contains materializable file blocks."""
    return bool(_BLOCK.search(text) or _FENCE_PATH.search(text))


def fix_missing_namespaces(xaml_path: Path) -> bool:
    """
    Auto-fix missing namespace declarations in XAML files.
    
    Checks for common namespace prefixes (ui:, uip:, snm:, etc.) and ensures
    the corresponding xmlns declarations are present in the root Activity element.
    Also fixes incorrect assembly references (mscorlib -> System.Private.CoreLib).
    
    Args:
        xaml_path: Path to XAML file to fix
        
    Returns:
        True if namespaces were added or fixed, False if no changes needed
    """
    try:
        content = xaml_path.read_text(encoding='utf-8')
        original_content = content
        fixed = False
        
        # Fix incorrect mscorlib reference for scg: (should be System.Private.CoreLib)
        if 'clr-namespace:System.Collections.Generic;assembly=mscorlib' in content:
            content = content.replace(
                'clr-namespace:System.Collections.Generic;assembly=mscorlib',
                'clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib'
            )
            fixed = True
        
        # Check for ui: prefix usage without xmlns:ui declaration
        if 'ui:' in content and 'xmlns:ui=' not in content:
            # Find the Activity opening tag and inject xmlns:ui
            # Look for xmlns:x declaration as anchor point
            if 'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"' in content:
                content = content.replace(
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"',
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n  xmlns:ui="http://schemas.uipath.com/workflow/activities"'
                )
                fixed = True
        
        # Check for snm:MailMessage usage without xmlns:snm declaration
        if 'snm:MailMessage' in content and 'xmlns:snm=' not in content:
            if 'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"' in content:
                content = content.replace(
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"',
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n  xmlns:snm="clr-namespace:System.Net.Mail;assembly=System.Net.Mail"'
                )
                fixed = True
        
        # Check for uip: prefix usage without xmlns:uip declaration
        if 'uip:' in content and 'xmlns:uip=' not in content:
            if 'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"' in content:
                content = content.replace(
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"',
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n  xmlns:uip="clr-namespace:UiPath.IntegrationService.Activities;assembly=UiPath.IntegrationService.Activities"'
                )
                fixed = True
        
        # Check for s: prefix usage without xmlns:s declaration (System namespace)
        if re.search(r'x:TypeArguments="s:', content) and 'xmlns:s=' not in content:
            if 'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"' in content:
                content = content.replace(
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"',
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n  xmlns:s="clr-namespace:System;assembly=System.Private.CoreLib"'
                )
                fixed = True
        
        # Check for scg: prefix usage without xmlns:scg declaration (System.Collections.Generic)
        if 'scg:' in content and 'xmlns:scg=' not in content:
            if 'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"' in content:
                content = content.replace(
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"',
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"\n  xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"'
                )
                fixed = True
        
        if fixed and content != original_content:
            xaml_path.write_text(content, encoding='utf-8')
            return True
        
        return False
    except Exception:
        return False


def materialize_from_assistant_text(
    text: str,
    output_root: Path,
    *,
    allow_project_files: bool = True,
) -> list[Path]:
    """
    Extract file blocks and write under output_root.

    Supported formats:
    1) <<<UIPATH_FILE path="relative/path">>>...<<<END_UIPATH_FILE>>>
    2) Markdown fence whose first line is ``path: relative/path`` then file body.
    
    Automatically fixes missing namespace declarations in XAML files.
    """
    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    listed: set[Path] = set()

    for m in _BLOCK.finditer(text):
        rel = m.group("rel")
        if not allow_project_files and _is_blocked_project_file(rel):
            continue
        body = m.group("body").strip("\n")
        dest = _write_under_root(root, rel, body)
        if dest is None:
            continue
        if dest not in listed:
            written.append(dest)
            listed.add(dest)

    for m in _FENCE_PATH.finditer(text):
        rel = m.group("rel").strip()
        if not allow_project_files and _is_blocked_project_file(rel):
            continue
        body = m.group("body").strip("\n")
        dest = _write_under_root(root, rel, body)
        if dest is None:
            continue
        if dest not in listed:
            written.append(dest)
            listed.add(dest)
    
    # Check environment variable once
    skip_activity_validation = os.environ.get(
        "UIPATH_SKIP_ACTIVITY_VALIDATION", "0"
    ).lower() in ("1", "true", "yes")
    
    # Import validator once if needed
    if not skip_activity_validation:
        from uipath_claude.validation.activity_validator import validate_activities_in_xaml
    
    # Auto-fix namespaces and validate activities in XAML files
    required_dependencies: set[str] = set()
    for path in written:
        if path.suffix.lower() == '.xaml':
            fix_missing_namespaces(path)
            try:
                xaml_content = path.read_text(encoding="utf-8")
            except Exception:
                xaml_content = ""
            if xaml_content:
                required_dependencies.update(_detect_required_dependencies(xaml_content))
            
            if not skip_activity_validation:
                success, errors = validate_activities_in_xaml(path)
                if not success:
                    for error in errors:
                        warnings.warn(f"Activity validation: {error}", UserWarning)
    if allow_project_files and required_dependencies:
        version_map = {package_id: version for package_id, version, _ in _DEPENDENCY_HINTS}
        for dependency in sorted(required_dependencies):
            version = version_map.get(dependency)
            if not version:
                continue
            _ensure_project_dependency(root, dependency, version)

    return written


def ensure_project_json(output_root: Path) -> bool:
    """
    Ensure a project.json exists in the output directory for validation.
    
    If project.json doesn't exist, creates a minimal template.
    
    Args:
        output_root: Path to the output directory
        
    Returns:
        True if project.json exists (or was created), False on error
    """
    project_json_path = output_root / "project.json"
    
    if project_json_path.exists():
        return True
    
    template = {
        "name": "GeneratedWorkflow",
        "description": "Generated UiPath workflow",
        "main": "Main.xaml",
        "dependencies": {
            "UiPath.System.Activities": "[24.10.6]",
            "UiPath.UIAutomation.Activities": "[24.10.8]"
        },
        "webServices": [],
        "entryPoints": [
            {
                "filePath": "Main.xaml",
                "uniqueId": str(uuid.uuid4()),
                "input": [],
                "output": []
            }
        ],
        "schemaVersion": "4.0",
        "studioVersion": "24.10.6",
        "projectVersion": "1.0.0",
        "runtimeOptions": {
            "autoDispose": False,
            "netFrameworkLazyLoading": False,
            "isPausable": True,
            "isAttended": False,
            "requiresUserInteraction": True,
            "supportsPersistence": False,
            "workflowSerialization": "DataContract",
            "excludedLoggedData": ["Private:*", "*password*"],
            "executionType": "Workflow",
            "readyForPiP": False,
            "startsInPiP": False,
            "mustRestoreAllDependencies": True,
            "pipType": "ChildSession"
        },
        "designOptions": {
            "projectProfile": "Developement",
            "outputType": "Process",
            "libraryOptions": {
                "includeOriginalXaml": False,
                "privateWorkflows": []
            },
            "processOptions": {
                "ignoredFiles": []
            },
            "fileInfoCollection": [],
            "modernBehavior": True
        },
        "expressionLanguage": "VisualBasic",
        "isTemplate": False,
        "templateProjectData": {},
        "publishData": {},
        "targetFramework": "Windows"
    }
    
    try:
        output_root.mkdir(parents=True, exist_ok=True)
        with open(project_json_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2)
        return True
    except Exception:
        return False


def _validate_xaml_structure(xaml_path: Path) -> tuple[bool, list[str]]:
    """
    Validate basic XAML structure without requiring Studio.
    
    Checks:
    - Valid XML syntax
    - Required root Activity element
    - Required namespace declarations
    - x:Class attribute presence
    - No forbidden/legacy activity patterns
    
    Returns:
        Tuple of (success, list of error messages)
    """
    import xml.etree.ElementTree as ET
    
    errors: list[str] = []
    
    try:
        content = xaml_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Failed to read file: {e}"]
    
    # Check for forbidden patterns (legacy/hallucinated activities)
    forbidden_patterns = [
        ("OutlookApplicationScope", "Legacy activity - use GetOutlookMailMessages directly"),
        ("ui:OutlookMailItem", "Hallucinated type - use snm:MailMessage"),
        ("OutlookMailApplication", "Legacy activity - use GetOutlookMailMessages directly"),
        ("GetOutlookQueuedEmails", "Hallucinated activity - use GetOutlookMailMessages"),
        ("ui:OutlookQueuedEmailMessage", "Hallucinated type - use snm:MailMessage"),
        ("StartOutlook", "Legacy scope activity - use GetOutlookMailMessages directly"),
        ("GetOutlookNamespace", "Legacy scope activity - use GetOutlookMailMessages directly"),
        ("GetOutlookFolder", "Legacy scope activity - use GetOutlookMailMessages directly"),
        ("ForEachOutlookMessageFile", "Legacy activity - use ui:ForEach with snm:MailMessage"),
        ("CreateMailMessage", "Hallucinated activity - use SendOutlookMail directly with To/Subject/Body"),
    ]
    
    for pattern, message in forbidden_patterns:
        if pattern in content:
            errors.append(f"Forbidden pattern '{pattern}': {message}")
    
    # Check for incorrect property usage
    if "GetOutlookMailMessages.Result" in content:
        errors.append("Incorrect property: Use Messages attribute instead of Result for GetOutlookMailMessages")
    
    # Try to parse as XML
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        errors.append(f"XML parse error: {e}")
        return False, errors
    
    # Check root element
    if not root.tag.endswith("}Activity") and root.tag != "Activity":
        errors.append(f"Root element should be Activity, got: {root.tag}")
    
    # Check for x:Class attribute
    x_class_found = False
    for attr in root.attrib:
        if attr.endswith("}Class") or attr == "Class":
            x_class_found = True
            break
    
    if not x_class_found:
        errors.append("Missing x:Class attribute on Activity element")
    
    # Check required namespaces by looking for their usage
    if "ui:" in content and 'xmlns:ui=' not in content:
        errors.append("Missing xmlns:ui declaration for ui: prefix activities")
    
    if "snm:" in content and 'xmlns:snm=' not in content:
        errors.append("Missing xmlns:snm declaration for snm: prefix types")
    
    if "scg:" in content and 'xmlns:scg=' not in content:
        errors.append("Missing xmlns:scg declaration for scg: prefix types")
    
    if "uip:" in content and 'xmlns:uip=' not in content:
        errors.append("Missing xmlns:uip declaration for Integration Service activities")
    
    return len(errors) == 0, errors


def _locate_project_root(root: Path) -> Path | None:
    """Resolve a UiPath project root that contains project.json."""
    if (root / "project.json").exists():
        return root
    if (root.parent / "project.json").exists():
        return root.parent
    try:
        for child in root.iterdir():
            if child.is_dir() and (child / "project.json").exists():
                return child
    except OSError:
        return None
    return None


def validate_generated_project(project_path: Path) -> dict:
    """Validate generated workflows with structure + Studio diagnostics.

    Validation stages:
    1) Structural XAML validation (always)
    2) File-level `uip rpa get-errors` validation (when a project + Studio are available)
    """
    from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_get_errors

    all_errors: list[str] = []
    all_warnings: list[str] = []

    xaml_files = list(project_path.rglob("*.xaml"))
    for xaml_file in xaml_files:
        ok, errors = _validate_xaml_structure(xaml_file)
        if not ok:
            all_errors.extend([f"[{xaml_file}] {err}" for err in errors])

    if all_errors:
        return {
            "valid": False,
            "success": False,
            "fully_validated": False,
            "errors": all_errors,
            "warnings": all_warnings,
            "project_path": str(project_path),
        }

    project_root = _locate_project_root(project_path)
    if project_root is None:
        all_warnings.append(
            "No project.json found. Structural validation passed; Studio diagnostics not run."
        )
        return {
            "valid": True,
            "success": True,
            "fully_validated": False,
            "errors": [],
            "warnings": all_warnings,
            "project_path": str(project_path),
        }

    studio_validation_ran = False
    for xaml_file in project_root.rglob("*.xaml"):
        rel = str(xaml_file.relative_to(project_root)).replace("\\", "/")
        cli_result = run_uip_rpa_get_errors(project_root, file_path=rel)

        if cli_result.get("studio_required"):
            all_warnings.append(
                "Studio diagnostics unavailable. Start/open the project in UiPath Studio "
                "to run `uip rpa get-errors`."
            )
            continue

        studio_validation_ran = True
        for warning in cli_result.get("warnings", []):
            all_warnings.append(f"[{rel}] {warning}")
        if not cli_result.get("success", False):
            for error in cli_result.get("errors", []):
                all_errors.append(f"[{rel}] {error}")

    success = len(all_errors) == 0
    return {
        "valid": success,
        "success": success,
        "fully_validated": studio_validation_ran,
        "errors": all_errors,
        "warnings": all_warnings,
        "project_path": str(project_root),
    }
