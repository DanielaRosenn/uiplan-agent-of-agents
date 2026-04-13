"""Tests for materialize_from_assistant_text."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

from uipath_claude.artifacts.materialize import (
    contains_file_blocks,
    ensure_project_json,
    materialize_from_assistant_text,
    validate_generated_project,
)


def test_materialize_writes_single_file(tmp_path: Path) -> None:
    root = tmp_path / "out"
    text = """
Some intro.
<<<UIPATH_FILE path="Main.xaml">>>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Root"><WriteLine Text="Hi" /></Sequence>
</Activity>
<<<END_UIPATH_FILE>>>
"""
    written = materialize_from_assistant_text(text, output_root=root)
    assert len(written) == 1
    assert written[0].exists()
    assert "WriteLine" in written[0].read_text(encoding="utf-8")


def test_materialize_rejects_parent_traversal(tmp_path: Path) -> None:
    root = tmp_path / "out"
    text = '<<<UIPATH_FILE path="../../../evil.txt">>>x<<<END_UIPATH_FILE>>>'
    written = materialize_from_assistant_text(text, output_root=root)
    assert written == []


def test_materialize_rejects_dotdot_in_middle(tmp_path: Path) -> None:
    root = tmp_path / "out"
    text = '<<<UIPATH_FILE path="foo/../bar.txt">>>x<<<END_UIPATH_FILE>>>'
    assert materialize_from_assistant_text(text, output_root=root) == []


def test_materialize_fence_path_format(tmp_path: Path) -> None:
    root = tmp_path / "out"
    text = '''Intro
```xml
path: sub/Note.md
# Hello
```
'''
    written = materialize_from_assistant_text(text, output_root=root)
    assert len(written) == 1
    assert written[0].read_text(encoding="utf-8") == "# Hello"


def test_materialize_rejects_absolute_windows_path(tmp_path: Path) -> None:
    if sys.platform != "win32":
        return
    root = tmp_path / "out"
    text = r'<<<UIPATH_FILE path="C:/Windows/Temp/evil.txt">>>x<<<END_UIPATH_FILE>>>'
    assert materialize_from_assistant_text(text, output_root=root) == []


def test_materialize_blocks_project_files_when_disallowed(tmp_path: Path) -> None:
    root = tmp_path / "out"
    text = """
<<<UIPATH_FILE path="project.json">>>
{"name":"BadProject"}
<<<END_UIPATH_FILE>>>
<<<UIPATH_FILE path="Main.xaml">>>
<Activity />
<<<END_UIPATH_FILE>>>
"""
    written = materialize_from_assistant_text(
        text,
        output_root=root,
        allow_project_files=False,
    )
    assert len(written) == 1
    assert written[0].name == "Main.xaml"
    assert not (root / "project.json").exists()


def test_contains_file_blocks_detects_uipath_markers() -> None:
    text = '<<<UIPATH_FILE path="Main.xaml">>><Activity /><<<END_UIPATH_FILE>>>'
    assert contains_file_blocks(text)


def test_ensure_project_json_creates_when_missing(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    
    assert not (root / "project.json").exists()
    result = ensure_project_json(root)
    
    assert result is True
    assert (root / "project.json").exists()
    
    data = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert data["name"] == "GeneratedWorkflow"
    assert data["main"] == "Main.xaml"
    assert data["targetFramework"] == "Windows"
    assert "UiPath.System.Activities" in data["dependencies"]


def test_ensure_project_json_returns_true_when_exists(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    existing = {"name": "ExistingProject", "main": "Custom.xaml"}
    (root / "project.json").write_text(json.dumps(existing), encoding="utf-8")
    
    result = ensure_project_json(root)
    
    assert result is True
    data = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert data["name"] == "ExistingProject"


def test_ensure_project_json_creates_parent_dirs(tmp_path: Path) -> None:
    root = tmp_path / "nested" / "deep" / "project"
    
    assert not root.exists()
    result = ensure_project_json(root)
    
    assert result is True
    assert (root / "project.json").exists()


def test_validate_generated_project_handles_nonexistent_path(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    result = validate_generated_project(missing)

    assert result["success"] is False
    assert result["project_path"] == str(missing.resolve())
    assert "does not exist or is not a directory" in result["errors"][0]


def test_validate_generated_project_creates_project_json_when_missing(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    with patch(
        "uipath_claude.tools.uipath.cli_runner.run_uip_rpa_analyze",
        return_value={"warnings": "careful"},
    ):
        result = validate_generated_project(project_root)

    assert (project_root / "project.json").exists()
    assert result["success"] is False
    assert result["errors"] == []
    assert result["warnings"] == ["careful"]
    assert result["project_path"] == str(project_root.resolve())


def test_validate_generated_project_runs_file_level_get_errors_loop(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "project.json").write_text("{}", encoding="utf-8")
    (project_root / "Main.xaml").write_text("<Activity />", encoding="utf-8")
    (project_root / "Flows").mkdir()
    (project_root / "Flows" / "Child.xaml").write_text("<Activity />", encoding="utf-8")

    with patch(
        "uipath_claude.tools.uipath.cli_runner.run_uip_rpa_analyze",
        return_value={"success": True, "errors": [], "warnings": []},
    ), patch(
        "uipath_claude.tools.uipath.cli_runner.run_uip_rpa_get_errors",
        return_value={"success": True, "errors": [], "diagnostics_ran": True},
    ) as mock_get_errors:
        result = validate_generated_project(project_root)

    assert result["success"] is True
    assert result["errors"] == []
    assert mock_get_errors.call_count == 2
    observed_paths = {
        Path(call.kwargs["file_path"]).relative_to(project_root).as_posix()
        for call in mock_get_errors.call_args_list
    }
    assert observed_paths == {"Main.xaml", "Flows/Child.xaml"}


def test_validate_generated_project_flags_when_diagnostics_not_run(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "project.json").write_text("{}", encoding="utf-8")
    (project_root / "Main.xaml").write_text("<Activity />", encoding="utf-8")

    with patch(
        "uipath_claude.tools.uipath.cli_runner.run_uip_rpa_analyze",
        return_value={"success": True, "errors": [], "warnings": []},
    ), patch(
        "uipath_claude.tools.uipath.cli_runner.run_uip_rpa_get_errors",
        return_value={
            "success": False,
            "errors": [
                "UiPath Studio is unavailable. File-level diagnostics could not run "
                "(interop/autopilot/dependency exception): Autopilot.Interop.DependencyException"
            ],
            "diagnostics_ran": False,
        },
    ):
        result = validate_generated_project(project_root)

    assert result["success"] is True
    assert result["fully_validated"] is False
    assert result["errors"] == []
    assert "warnings" in result
    assert "File-level diagnostics not run for Main.xaml" in result["warnings"][0]


def test_validate_generated_project_skips_file_diagnostics_on_structural_failure(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "project.json").write_text("{}", encoding="utf-8")
    (project_root / "Main.xaml").write_text("<Activity />", encoding="utf-8")

    with patch(
        "uipath_claude.tools.uipath.cli_runner.run_uip_rpa_analyze",
        return_value={"success": False, "errors": ["Broken project"], "warnings": []},
    ), patch(
        "uipath_claude.tools.uipath.cli_runner.run_uip_rpa_get_errors"
    ) as mock_get_errors:
        result = validate_generated_project(project_root)

    assert result["success"] is False
    assert result["errors"] == ["Broken project"]
    mock_get_errors.assert_not_called()
