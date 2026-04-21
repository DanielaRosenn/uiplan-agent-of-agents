"""Unit tests for ``uipath_claude.tools.xaml_tools`` renderer.

Each supported activity kind must:

1. Render successfully from a minimal spec.
2. Produce well-formed XML (parseable by ``xml.etree.ElementTree``).
3. Pass ``validate_xaml_text`` with zero errors.
4. Include the expected activity tag in the output.

The tests also cover argument-name validation, variable validation, and
write-to-disk via ``create_xaml_workflow``.
"""
from __future__ import annotations

import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from uipath_claude.tools.xaml_tools import (
    XamlRenderError,
    create_xaml_workflow,
    render_xaml_workflow,
    validate_xaml_text,
)


def _render_with_body(body: list[dict], **kwargs) -> str:
    return render_xaml_workflow(
        relative_path="Workflows/T.xaml",
        variables=kwargs.pop(
            "variables",
            [{"name": "tmp", "type": "x:String"}],
        ),
        body=body,
        **kwargs,
    )


def _expect_clean(xaml: str, relative_path: str = "Workflows/T.xaml") -> None:
    ET.fromstring(xaml)  # well-formed
    issues = validate_xaml_text(xaml, relative_path=relative_path)
    errors = [i for i in issues if i.level == "error"]
    assert not errors, f"Validator errors: {errors}"


def test_sequence_and_log_message() -> None:
    xaml = _render_with_body(
        [{"kind": "LogMessage", "message_expr": '"hi"'}]
    )
    assert "ui:LogMessage" in xaml
    _expect_clean(xaml)


def test_write_line() -> None:
    xaml = _render_with_body(
        [{"kind": "WriteLine", "text_expr": '"line"'}]
    )
    assert "<WriteLine" in xaml
    _expect_clean(xaml)


def test_assign_binds_target_and_value() -> None:
    xaml = _render_with_body(
        [{"kind": "Assign", "to": "tmp", "value_expr": '"hello"'}]
    )
    assert "<Assign" in xaml
    assert "<Assign.To>" in xaml
    assert "<Assign.Value>" in xaml
    assert "[tmp]" in xaml
    _expect_clean(xaml)


def test_if_then_only() -> None:
    xaml = _render_with_body(
        [
            {
                "kind": "If",
                "condition_expr": "true",
                "then": [{"kind": "WriteLine", "text_expr": '"yes"'}],
            }
        ]
    )
    assert "<If " in xaml
    assert "If.Then" in xaml
    _expect_clean(xaml)


def test_if_with_then_and_else_wraps_multi_activities_in_sequence() -> None:
    xaml = _render_with_body(
        [
            {
                "kind": "If",
                "condition_expr": "true",
                "then": [
                    {"kind": "WriteLine", "text_expr": '"a"'},
                    {"kind": "WriteLine", "text_expr": '"b"'},
                ],
                "else": [{"kind": "WriteLine", "text_expr": '"c"'}],
            }
        ]
    )
    assert xaml.count("<Sequence") >= 2  # outer + then wrapper
    _expect_clean(xaml)


def test_while_and_do_while() -> None:
    xaml = _render_with_body(
        [
            {"kind": "While", "condition_expr": "false",
             "body": [{"kind": "WriteLine", "text_expr": '"w"'}]},
            {"kind": "DoWhile", "condition_expr": "false",
             "body": [{"kind": "WriteLine", "text_expr": '"d"'}]},
        ]
    )
    assert "<While " in xaml
    assert "<DoWhile " in xaml
    _expect_clean(xaml)


def test_for_each_emits_item_type() -> None:
    xaml = _render_with_body(
        [
            {
                "kind": "ForEach",
                "item_name": "f",
                "item_type": "x:String",
                "values_expr": "new string[]{}",
                "body": [{"kind": "WriteLine", "text_expr": "f"}],
            }
        ]
    )
    assert "ui:ForEach" in xaml
    assert "ui:ForEach.Body" in xaml
    assert 'Name="f"' in xaml
    _expect_clean(xaml)


def test_try_catch_with_finally() -> None:
    xaml = _render_with_body(
        [
            {
                "kind": "TryCatch",
                "try": [{"kind": "WriteLine", "text_expr": '"t"'}],
                "catches": [
                    {
                        "exception_type": "System.Exception",
                        "var": "ex",
                        "body": [
                            {"kind": "LogMessage", "level": "Error",
                             "message_expr": "ex.Message"}
                        ],
                    }
                ],
                "finally": [{"kind": "WriteLine", "text_expr": '"fin"'}],
            }
        ]
    )
    assert "<TryCatch" in xaml
    assert "TryCatch.Catches" in xaml
    assert "TryCatch.Finally" in xaml
    _expect_clean(xaml)


def test_throw_requires_exception_expression() -> None:
    with pytest.raises(XamlRenderError, match="Throw requires"):
        _render_with_body([{"kind": "Throw"}])


def test_invoke_workflow_arguments_in_out_inout() -> None:
    xaml = _render_with_body(
        [
            {
                "kind": "InvokeWorkflow",
                "file": "Workflows/Sub.xaml",
                "arguments": {
                    "in_A": "tmp",
                    "out_B": {"direction": "Out", "expr": "tmp"},
                    "io_C": {"direction": "InOut", "expr": "tmp"},
                },
            }
        ]
    )
    assert "ui:InvokeWorkflowFile" in xaml
    assert '<InArgument x:TypeArguments="x:String" x:Key="in_A">[tmp]</InArgument>' in xaml
    assert 'x:Key="out_B"' in xaml
    assert "<InOutArgument" in xaml
    _expect_clean(xaml)


def test_read_and_write_text_file() -> None:
    xaml = _render_with_body(
        [
            {"kind": "ReadTextFile",
             "file_name_expr": '"in.txt"', "content_var": "tmp"},
            {"kind": "WriteTextFile",
             "file_name_expr": '"out.txt"', "text_expr": "tmp"},
            {"kind": "AppendLine",
             "file_name_expr": '"log.txt"', "text_expr": '"done"'},
        ]
    )
    assert "ui:ReadTextFile" in xaml
    assert "ui:WriteTextFile" in xaml
    assert "ui:AppendLine" in xaml
    _expect_clean(xaml)


def test_create_directory_emits_invoke_method() -> None:
    xaml = _render_with_body(
        [{"kind": "CreateDirectory", "path_expr": '"C:\\\\tmp"'}]
    )
    assert "<InvokeMethod" in xaml
    assert "MethodName=\"CreateDirectory\"" in xaml
    assert "io:Directory" in xaml
    assert "{x:Type io:Directory}" in xaml
    _expect_clean(xaml)


def test_argument_name_convention_is_enforced() -> None:
    with pytest.raises(XamlRenderError, match="UiPath convention"):
        render_xaml_workflow(
            relative_path="Workflows/Bad.xaml",
            arguments=[{"name": "inFilePath", "direction": "In", "type": "x:String"}],
            body=[],
        )


def test_variable_without_type_is_rejected() -> None:
    with pytest.raises(XamlRenderError):
        render_xaml_workflow(
            relative_path="Workflows/Bad.xaml",
            variables=[{"name": "x"}],
            body=[],
        )


def test_unknown_activity_kind_is_rejected() -> None:
    with pytest.raises(XamlRenderError, match="Unknown activity kind"):
        _render_with_body([{"kind": "NotARealKind"}])


def test_x_class_is_derived_from_path() -> None:
    xaml = render_xaml_workflow(
        relative_path="Workflows/ExtractInvoice.xaml", body=[]
    )
    assert 'x:Class="Workflows_ExtractInvoice"' in xaml


def test_create_xaml_workflow_writes_file_and_reports_ok() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "proj"
        proj.mkdir()
        (proj / "project.json").write_text(
            json.dumps({"name": "demo"}), encoding="utf-8"
        )
        result = create_xaml_workflow.func(  # type: ignore[attr-defined]
            project_dir=str(proj),
            relative_path="Workflows/Demo.xaml",
            body=[{"kind": "LogMessage", "message_expr": '"hi"'}],
        )
        assert "[OK]" in result
        assert "0 errors" in result
        assert (proj / "Workflows" / "Demo.xaml").exists()


def test_create_xaml_workflow_rejects_non_absolute_project_dir() -> None:
    result = create_xaml_workflow.func(  # type: ignore[attr-defined]
        project_dir="not/absolute",
        relative_path="Workflows/Demo.xaml",
        body=[],
    )
    assert "[ERROR]" in result
    assert "absolute" in result.lower()


def test_create_xaml_workflow_rejects_missing_project_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = create_xaml_workflow.func(  # type: ignore[attr-defined]
            project_dir=str(Path(tmp).resolve()),
            relative_path="Workflows/Demo.xaml",
            body=[],
        )
        assert "[ERROR]" in result
        assert "project.json" in result.lower()


def test_create_xaml_workflow_rejects_path_escape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "proj"
        proj.mkdir()
        (proj / "project.json").write_text("{}", encoding="utf-8")
        result = create_xaml_workflow.func(  # type: ignore[attr-defined]
            project_dir=str(proj),
            relative_path="../escape.xaml",
            body=[],
        )
        assert "[ERROR]" in result
        assert "escape" in result.lower() or "project_dir" in result.lower()
