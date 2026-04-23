#!/usr/bin/env python3
"""Regenerate InvoiceIntake_Demo XAML from the deterministic renderer (demo-safe)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJ = ROOT / "InvoiceIntake_Demo"
_fw = ROOT / "framework"
sys.path.insert(0, str(_fw if (_fw / "uipath_claude").is_dir() else ROOT))

from uipath_claude.tools.xaml_tools import render_xaml_workflow, validate_xaml_text  # noqa: E402


def _write(rel: str, xml: str) -> None:
    dest = PROJ / rel.replace("/", "\\")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(xml, encoding="utf-8")
    issues = validate_xaml_text(xml, project_dir=PROJ, relative_path=rel)
    errs = [i for i in issues if i.level == "error"]
    if errs:
        print(f"ERROR {rel}:")
        for e in errs:
            print(f"  {e.message}")
        sys.exit(1)
    print(f"OK {rel} ({len(xml)} bytes)")


def main() -> None:
    if not (PROJ / "project.json").exists():
        print(f"Missing project: {PROJ}")
        sys.exit(1)

    # --- Workflows/ExtractInvoice.xaml ---
    extract = render_xaml_workflow(
        "Workflows/ExtractInvoice.xaml",
        arguments=[
            {"name": "in_InvoiceFilePath", "direction": "In", "type": "x:String"},
            {"name": "out_InvoiceData", "direction": "Out", "type": "x:String"},
        ],
        variables=[{"name": "extractedText", "type": "x:String", "default": '""'}],
        body=[
            {
                "kind": "LogMessage",
                "display_name": "Log extract target path",
                "message_expr": '"[ExtractInvoice] File: " + in_InvoiceFilePath',
            },
            {
                "kind": "ReadTextFile",
                "display_name": "Read invoice file into text",
                "file_name_expr": "in_InvoiceFilePath",
                "content_var": "extractedText",
            },
            {
                "kind": "Assign",
                "to": "out_InvoiceData",
                "to_type": "x:String",
                "to_direction": "Out",
                "value_expr": "extractedText",
            },
        ],
    )
    _write("Workflows/ExtractInvoice.xaml", extract)

    # --- Workflows/ApplyPolicy.xaml (length rule from demo spec) ---
    apply_policy = render_xaml_workflow(
        "Workflows/ApplyPolicy.xaml",
        arguments=[
            {"name": "in_InvoiceData", "direction": "In", "type": "x:String"},
            {"name": "out_PolicyResult", "direction": "Out", "type": "x:String"},
        ],
        body=[
            {
                "kind": "LogMessage",
                "display_name": "Log policy evaluation start",
                "message_expr": '"[ApplyPolicy] Evaluating invoice payload length"',
            },
            {
                "kind": "If",
                "display_name": "Check minimum content",
                "condition_expr": "in_InvoiceData.Length < 10",
                "then": [
                    {
                        "kind": "Assign",
                        "display_name": "Set policy result rejected",
                        "to": "out_PolicyResult",
                        "to_type": "x:String",
                        "to_direction": "Out",
                        "value_expr": '"Rejected: no data"',
                    }
                ],
                "else": [
                    {
                        "kind": "Assign",
                        "display_name": "Set policy result approved",
                        "to": "out_PolicyResult",
                        "to_type": "x:String",
                        "to_direction": "Out",
                        "value_expr": '"Approved: Standard approval"',
                    }
                ],
            },
        ],
    )
    _write("Workflows/ApplyPolicy.xaml", apply_policy)

    # --- Workflows/WriteResult.xaml ---
    out_path = (
        'Path.Combine(Directory.GetCurrentDirectory(), "Data", "Output", '
        'System.IO.Path.GetFileNameWithoutExtension(in_FileName) + "_result.txt")'
    )
    body_text = (
        '"Invoice file: " + in_FileName + System.Environment.NewLine + '
        '"---" + System.Environment.NewLine + '
        '"Extracted data:" + System.Environment.NewLine + in_InvoiceData + '
        'System.Environment.NewLine + "---" + System.Environment.NewLine + '
        '"Policy:" + System.Environment.NewLine + in_PolicyResult'
    )
    write_result = render_xaml_workflow(
        "Workflows/WriteResult.xaml",
        arguments=[
            {"name": "in_FileName", "direction": "In", "type": "x:String"},
            {"name": "in_InvoiceData", "direction": "In", "type": "x:String"},
            {"name": "in_PolicyResult", "direction": "In", "type": "x:String"},
        ],
        body=[
            {
                "kind": "LogMessage",
                "display_name": "Log write result path",
                "message_expr": (
                    '"[WriteResult] Output path: " + System.IO.Path.GetFileNameWithoutExtension'
                    '(in_FileName) + "_result.txt"'
                ),
            },
            {
                "kind": "WriteTextFile",
                "display_name": "Write result file",
                "file_name_expr": out_path,
                "text_expr": body_text,
            },
        ],
    )
    _write("Workflows/WriteResult.xaml", write_result)

    # --- Main.xaml ---
    main_body: list[dict] = [
        {
            "kind": "LogMessage",
            "display_name": "Log intake started",
            "message_expr": '"[Main] Invoice intake started"',
        },
        {
            "kind": "Assign",
            "display_name": "Resolve input folder",
            "to": "inputDir",
            "to_type": "x:String",
            "to_direction": "Out",
            "value_expr": 'Path.Combine(Directory.GetCurrentDirectory(), "Data", "Input")',
        },
        {"kind": "CreateDirectory", "display_name": "Ensure Data/Input", "path_expr": "inputDir"},
        {
            "kind": "CreateDirectory",
            "display_name": "Ensure Data/Output",
            "path_expr": 'Path.Combine(Directory.GetCurrentDirectory(), "Data", "Output")',
        },
        # Avoid ``?:`` ternary — UiPath expression validation rejects ``?`` here.
        {
            "kind": "If",
            "display_name": "Prefer PDF files else TXT",
            "condition_expr": 'Directory.GetFiles(inputDir, "*.pdf").Length > 0',
            "then": [
                {
                    "kind": "Assign",
                    "display_name": "Assign PDF list",
                    "to": "files",
                    "to_type": "s:String[]",
                    "to_direction": "Out",
                    "value_expr": 'Directory.GetFiles(inputDir, "*.pdf")',
                }
            ],
            "else": [
                {
                    "kind": "Assign",
                    "display_name": "Assign TXT list",
                    "to": "files",
                    "to_type": "s:String[]",
                    "to_direction": "Out",
                    "value_expr": 'Directory.GetFiles(inputDir, "*.txt")',
                }
            ],
        },
        {
            "kind": "LogMessage",
            "display_name": "Log file count",
            "message_expr": '"[Main] Files to process: " + files.Length.ToString()',
        },
        {
            "kind": "ForEach",
            "display_name": "For each invoice file",
            "item_name": "currentFile",
            "item_type": "x:String",
            "values_expr": "files",
            "body": [
                {
                    "kind": "TryCatch",
                    "display_name": "Process with error handling",
                    "try": [
                        {
                            "kind": "InvokeWorkflow",
                            "display_name": "Extract",
                            "file": "Workflows/ExtractInvoice.xaml",
                            "arguments": {
                                "in_InvoiceFilePath": "currentFile",
                                "out_InvoiceData": {
                                    "direction": "Out",
                                    "expr": "invoiceData",
                                },
                            },
                        },
                        {
                            "kind": "InvokeWorkflow",
                            "display_name": "Apply policy",
                            "file": "Workflows/ApplyPolicy.xaml",
                            "arguments": {
                                "in_InvoiceData": "invoiceData",
                                "out_PolicyResult": {
                                    "direction": "Out",
                                    "expr": "policyResult",
                                },
                            },
                        },
                        {
                            "kind": "InvokeWorkflow",
                            "display_name": "Write result",
                            "file": "Workflows/WriteResult.xaml",
                            "arguments": {
                                "in_FileName": 'System.IO.Path.GetFileName(currentFile)',
                                "in_InvoiceData": "invoiceData",
                                "in_PolicyResult": "policyResult",
                            },
                        },
                        {
                            "kind": "LogMessage",
                            "display_name": "Log file processed OK",
                            "message_expr": (
                                '"[Main] Finished: " + System.IO.Path.GetFileName(currentFile)'
                            ),
                        },
                    ],
                    "catches": [
                        {
                            "exception_type": "System.Exception",
                            "var": "ex",
                            "body": [
                                {
                                    "kind": "LogMessage",
                                    "display_name": "Log processing failure",
                                    "level": "Error",
                                    "message_expr": (
                                        '"[Main] Failed on " + currentFile + ": " + ex.Message'
                                    ),
                                }
                            ],
                        }
                    ],
                }
            ],
        },
        {
            "kind": "LogMessage",
            "display_name": "Log intake completed",
            "message_expr": '"[Main] Invoice intake completed"',
        },
    ]

    main = render_xaml_workflow(
        "Main.xaml",
        variables=[
            {
                "name": "inputDir",
                "type": "x:String",
                "default": '""',
            },
            {
                "name": "files",
                "type": "s:String[]",
            },
            {"name": "invoiceData", "type": "x:String", "default": '""'},
            {"name": "policyResult", "type": "x:String", "default": '""'},
        ],
        body=main_body,
    )
    _write("Main.xaml", main)
    print("All XAML regenerated and passed validate_xaml_text.")


if __name__ == "__main__":
    main()
