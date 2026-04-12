"""Materialize file blocks from assistant text (deterministic writes)."""
from __future__ import annotations

import json
import re
import uuid
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
    
    # Auto-fix missing namespaces in XAML files
    for path in written:
        if path.suffix.lower() == '.xaml':
            fix_missing_namespaces(path)

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


def validate_generated_project(project_path: Path) -> dict:
    """Validate a generated UiPath project using uip CLI.
    
    Returns dict with:
        - success: bool
        - errors: list of error strings
        - project_path: str
    """
    from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_get_errors
    
    project_json = project_path / "project.json"
    if not project_json.exists():
        parent = project_path.parent
        if (parent / "project.json").exists():
            project_path = parent
        else:
            for child in project_path.iterdir():
                if child.is_dir() and (child / "project.json").exists():
                    project_path = child
                    break
    
    if not (project_path / "project.json").exists():
        if not ensure_project_json(project_path):
            return {
                "success": False,
                "errors": ["No project.json found and failed to create template"],
                "project_path": str(project_path),
            }
    
    result = run_uip_rpa_get_errors(project_path)
    return {
        "success": result["success"],
        "errors": result["errors"],
        "project_path": str(project_path),
    }
