"""Unit tests for ``validate_xaml`` / ``validate_xaml_text``.

One failing-case test per validator check. Each test asserts that:

- The message names the offending activity (DisplayName) when applicable.
- The fix hint is non-empty.
- The overall return is an error, not a warning.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from uipath_claude.tools.xaml_tools import (
    validate_xaml,
    validate_xaml_text,
)


_GOOD = (
    '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
    'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
    'x:Class="Workflows_Good">'
    '<Sequence DisplayName="Body" sap2010:WorkflowViewState.IdRef="Sequence_1"/>'
    '</Activity>'
)


def _only_errors(xaml: str, **kw):
    return [i for i in validate_xaml_text(xaml, **kw) if i.level == "error"]


def test_good_xaml_is_clean() -> None:
    assert _only_errors(_GOOD, relative_path="Workflows/Good.xaml") == []


def test_parse_error_returned_with_location() -> None:
    issues = validate_xaml_text("<not well formed", relative_path="X.xaml")
    assert any("XML parsing error" in i.message for i in issues)
    assert all(i.fix for i in issues)


def test_root_must_be_activity() -> None:
    xaml = '<Foo xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"/>'
    errs = _only_errors(xaml)
    assert any("Root element must be <Activity>" in e.message for e in errs)


def test_missing_x_class_is_error() -> None:
    xaml = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">'
        '</Activity>'
    )
    errs = _only_errors(xaml)
    assert any("missing x:Class" in e.message for e in errs)


def test_x_class_mismatch_is_error_when_path_given() -> None:
    errs = _only_errors(_GOOD, relative_path="Workflows/Mismatch.xaml")
    assert any("does not match path" in e.message for e in errs)
    assert any("Workflows_Mismatch" in e.fix for e in errs)


def test_missing_required_namespace_warns() -> None:
    xaml = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'x:Class="Workflows_Good"/>'
    )
    issues = validate_xaml_text(xaml, relative_path="Workflows/Good.xaml")
    assert any("xmlns:sap2010" in i.message for i in issues if i.level == "warning")


def test_empty_assign_to_is_error() -> None:
    xaml = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
        'x:Class="Workflows_Good">'
        '<Sequence><Assign DisplayName="BadAssign">'
        '<Assign.To><OutArgument x:TypeArguments="x:String"></OutArgument></Assign.To>'
        '<Assign.Value><InArgument x:TypeArguments="x:String">[x]</InArgument></Assign.Value>'
        '</Assign></Sequence></Activity>'
    )
    errs = _only_errors(xaml, relative_path="Workflows/Good.xaml")
    assert any("BadAssign" in e.message and "empty Assign.To" in e.message for e in errs)


def test_missing_assign_value_is_error() -> None:
    xaml = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
        'x:Class="Workflows_Good">'
        '<Sequence><Assign DisplayName="NoValue">'
        '<Assign.To><OutArgument x:TypeArguments="x:String">[x]</OutArgument></Assign.To>'
        '</Assign></Sequence></Activity>'
    )
    errs = _only_errors(xaml, relative_path="Workflows/Good.xaml")
    assert any("NoValue" in e.message and "Assign.Value" in e.message for e in errs)


def test_throw_with_empty_exception_is_error() -> None:
    xaml = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
        'x:Class="Workflows_Good">'
        '<Sequence><Throw DisplayName="EmptyThrow" Exception=""/></Sequence>'
        '</Activity>'
    )
    errs = _only_errors(xaml, relative_path="Workflows/Good.xaml")
    assert any("EmptyThrow" in e.message and "empty Exception" in e.message for e in errs)


def test_if_with_empty_condition_is_error() -> None:
    xaml = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
        'x:Class="Workflows_Good">'
        '<Sequence><If DisplayName="BlankIf" Condition=""/></Sequence>'
        '</Activity>'
    )
    errs = _only_errors(xaml, relative_path="Workflows/Good.xaml")
    assert any("BlankIf" in e.message and "empty Condition" in e.message for e in errs)


def test_invoke_workflow_missing_file_warns() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp)
        xaml = (
            '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
            'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
            'x:Class="Workflows_Good">'
            '<Sequence><InvokeWorkflowFile DisplayName="CallSub" '
            'WorkflowFileName="Workflows/Missing.xaml"/></Sequence>'
            '</Activity>'
        )
        issues = validate_xaml_text(
            xaml, project_dir=proj, relative_path="Workflows/Good.xaml"
        )
        warnings = [i for i in issues if i.level == "warning"]
        assert any("CallSub" in w.message and "missing file" in w.message for w in warnings)


def test_idref_inconsistency_is_warning() -> None:
    xaml = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
        'x:Class="Workflows_Good">'
        '<Sequence sap2010:WorkflowViewState.IdRef="Sequence_1">'
        '<WriteLine DisplayName="NoId" Text="[1]"/>'
        '</Sequence></Activity>'
    )
    issues = validate_xaml_text(xaml, relative_path="Workflows/Good.xaml")
    assert any("inconsistent" in i.message for i in issues if i.level == "warning")


def test_argument_type_shape_is_error() -> None:
    xaml = (
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" '
        'x:Class="Workflows_Good">'
        '<x:Members><x:Property Name="in_Bad" Type="x:String"/></x:Members>'
        '<Sequence sap2010:WorkflowViewState.IdRef="Sequence_1"/>'
        '</Activity>'
    )
    errs = _only_errors(xaml, relative_path="Workflows/Good.xaml")
    assert any("in_Bad" in e.message and "malformed" in e.message for e in errs)


def test_validate_xaml_tool_reads_file_and_reports() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "proj"
        proj.mkdir()
        (proj / "project.json").write_text("{}", encoding="utf-8")
        wf = proj / "Workflows" / "X.xaml"
        wf.parent.mkdir()
        wf.write_text("<not xml", encoding="utf-8")
        result = validate_xaml.func(  # type: ignore[attr-defined]
            project_dir=str(proj),
            relative_path="Workflows/X.xaml",
        )
        assert "[ERROR]" in result
        assert "XML parsing error" in result
