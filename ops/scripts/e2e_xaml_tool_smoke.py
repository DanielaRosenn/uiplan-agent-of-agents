"""End-to-end smoke for the XAML authoring tool against InvoiceIntake_Demo.

Mirrors the exact tool calls a chat agent would make to produce the
four-workflow invoice-intake project. Runs strictly through
``create_xaml_workflow`` + ``validate_xaml``; does not touch Studio or
``uipcli``. A pass means:

- Every sub-workflow renders as well-formed XAML.
- Every file passes the schema-aware validator.
- Every cross-workflow ``InvokeWorkflow`` reference resolves on disk.

Pair with ``scripts/dryrun_invoice_demo.py`` to verify the runtime logic,
and with ``uipcli package analyze`` (run by the user from Studio's
terminal) to confirm Studio accepts the XAML.

Exit code 0 + ``E2E OK`` means the XAML-authoring foundation is sound.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from uipath_claude.tools.xaml_tools import create_xaml_workflow, validate_xaml


PROJECT_DIR = Path(
    os.environ.get(
        "UIPATH_INVOICE_DEMO_DIR",
        r"C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath\InvoiceIntake_Demo",
    )
)


def _ensure_project_dir() -> None:
    if not PROJECT_DIR.exists():
        sys.exit(f"E2E FAIL: project_dir does not exist: {PROJECT_DIR}")
    if not (PROJECT_DIR / "project.json").exists():
        sys.exit(f"E2E FAIL: project.json missing in {PROJECT_DIR}")


def _reset_workflows() -> None:
    """Wipe any previously generated XAML so the run is clean.

    OneDrive/Studio can hold a lock on the directory itself; delete only
    the .xaml files under it rather than the directory.
    """
    wf = PROJECT_DIR / "Workflows"
    wf.mkdir(exist_ok=True)
    for child in wf.glob("*.xaml"):
        try:
            child.unlink()
        except OSError:
            pass
    # Main.xaml is at project root; best-effort delete so the renderer re-emits it.
    main = PROJECT_DIR / "Main.xaml"
    if main.exists():
        try:
            main.unlink()
        except OSError:
            pass


def _must_ok(label: str, result: str) -> None:
    if "[OK]" not in result:
        sys.exit(f"E2E FAIL [{label}]:\n{result}")
    print(f"  [OK] {label}")


def _build_extract_invoice() -> dict:
    return {
        "project_dir": str(PROJECT_DIR),
        "relative_path": "Workflows/ExtractInvoice.xaml",
        "arguments": [
            {"name": "in_FilePath", "direction": "In", "type": "x:String"},
            {
                "name": "out_Fields",
                "direction": "Out",
                "type": "scg:Dictionary(x:String, x:String)",
            },
        ],
        "variables": [
            {"name": "rawText", "type": "x:String"},
        ],
        "body": [
            {
                "kind": "ReadTextFile",
                "file_name_expr": "in_FilePath",
                "content_var": "rawText",
            },
            {
                "kind": "Assign",
                "to": "out_Fields",
                "to_type": "scg:Dictionary(x:String, x:String)",
                "value_expr": "new System.Collections.Generic.Dictionary<System.String, System.String>()",
            },
            {
                "kind": "If",
                "condition_expr": "String.IsNullOrWhiteSpace(rawText)",
                "then": [
                    {
                        "kind": "Throw",
                        "exception_expr": "new System.Exception(\"empty invoice: \" + in_FilePath)",
                    }
                ],
            },
        ],
    }


def _build_apply_policy() -> dict:
    return {
        "project_dir": str(PROJECT_DIR),
        "relative_path": "Workflows/ApplyPolicy.xaml",
        "arguments": [
            {
                "name": "in_Fields",
                "direction": "In",
                "type": "scg:Dictionary(x:String, x:String)",
            },
            {"name": "out_Decision", "direction": "Out", "type": "x:String"},
        ],
        "body": [
            {
                "kind": "Assign",
                "to": "out_Decision",
                "value_expr": "\"approved\"",
            },
            {
                "kind": "LogMessage",
                "message_expr": "\"Decision: \" + out_Decision",
            },
        ],
    }


def _build_write_result() -> dict:
    return {
        "project_dir": str(PROJECT_DIR),
        "relative_path": "Workflows/WriteResult.xaml",
        "arguments": [
            {"name": "in_FilePath", "direction": "In", "type": "x:String"},
            {"name": "in_Decision", "direction": "In", "type": "x:String"},
            {
                "name": "in_Fields",
                "direction": "In",
                "type": "scg:Dictionary(x:String, x:String)",
            },
        ],
        "variables": [
            {"name": "outputPath", "type": "x:String"},
        ],
        "body": [
            {
                "kind": "Assign",
                "to": "outputPath",
                "value_expr": (
                    "System.IO.Path.Combine(\"Data\\\\Output\", "
                    "System.IO.Path.GetFileNameWithoutExtension(in_FilePath) + \".json\")"
                ),
            },
            {
                "kind": "CreateDirectory",
                "path_expr": "System.IO.Path.GetDirectoryName(outputPath)",
            },
            {
                "kind": "WriteTextFile",
                "file_name_expr": "outputPath",
                "text_expr": (
                    "\"{\\\"decision\\\":\\\"\" + in_Decision + \"\\\"}\""
                ),
            },
        ],
    }


def _build_main() -> dict:
    return {
        "project_dir": str(PROJECT_DIR),
        "relative_path": "Main.xaml",
        "variables": [
            {"name": "invoiceFiles", "type": "scg:IEnumerable(x:String)"},
            {"name": "extracted", "type": "scg:Dictionary(x:String, x:String)"},
            {"name": "decision", "type": "x:String"},
        ],
        "body": [
            {
                "kind": "Assign",
                "to": "invoiceFiles",
                "to_type": "scg:IEnumerable(x:String)",
                "value_expr": "System.IO.Directory.EnumerateFiles(\"Data\\\\Input\", \"*.pdf\")",
            },
            {
                "kind": "ForEach",
                "item_name": "currentFile",
                "item_type": "x:String",
                "values_expr": "invoiceFiles",
                "body": [
                    {
                        "kind": "InvokeWorkflow",
                        "file": "Workflows\\ExtractInvoice.xaml",
                        "arguments": {
                            "in_FilePath": {"direction": "In", "expr": "currentFile"},
                            "out_Fields": {"direction": "Out", "expr": "extracted"},
                        },
                        "argument_types": {
                            "in_FilePath": "x:String",
                            "out_Fields": "scg:Dictionary(x:String, x:String)",
                        },
                    },
                    {
                        "kind": "InvokeWorkflow",
                        "file": "Workflows\\ApplyPolicy.xaml",
                        "arguments": {
                            "in_Fields": {"direction": "In", "expr": "extracted"},
                            "out_Decision": {"direction": "Out", "expr": "decision"},
                        },
                        "argument_types": {
                            "in_Fields": "scg:Dictionary(x:String, x:String)",
                            "out_Decision": "x:String",
                        },
                    },
                    {
                        "kind": "InvokeWorkflow",
                        "file": "Workflows\\WriteResult.xaml",
                        "arguments": {
                            "in_FilePath": "currentFile",
                            "in_Decision": "decision",
                            "in_Fields": {
                                "direction": "In",
                                "expr": "extracted",
                            },
                        },
                        "argument_types": {
                            "in_FilePath": "x:String",
                            "in_Decision": "x:String",
                            "in_Fields": "scg:Dictionary(x:String, x:String)",
                        },
                    },
                ],
            },
            {
                "kind": "LogMessage",
                "level": "Info",
                "message_expr": "\"Invoice intake finished.\"",
            },
        ],
    }


def main() -> int:
    _ensure_project_dir()
    _reset_workflows()
    print(f"E2E target: {PROJECT_DIR}")

    # Order matters: subs first (so Main's validator sees them on disk).
    for label, spec in (
        ("ExtractInvoice", _build_extract_invoice()),
        ("ApplyPolicy", _build_apply_policy()),
        ("WriteResult", _build_write_result()),
        ("Main", _build_main()),
    ):
        result = create_xaml_workflow.func(**spec)  # type: ignore[attr-defined]
        _must_ok(f"create {label}", result)

    # Re-validate every file end-to-end.
    for rel in (
        "Workflows/ExtractInvoice.xaml",
        "Workflows/ApplyPolicy.xaml",
        "Workflows/WriteResult.xaml",
        "Main.xaml",
    ):
        result = validate_xaml.func(  # type: ignore[attr-defined]
            project_dir=str(PROJECT_DIR),
            relative_path=rel,
        )
        _must_ok(f"validate {rel}", result)

    print("E2E OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
