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


def test_validate_generated_project_includes_activity_validation_errors(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "project.json").write_text('{"name":"Test","main":"Main.xaml"}', encoding="utf-8")
    (root / "Main.xaml").write_text("<Activity><ui:FakeHallucinatedActivity/></Activity>", encoding="utf-8")

    with patch("uipath_claude.tools.uipath.cli_runner.run_uip_rpa_analyze") as mock_analyze:
        mock_analyze.return_value = {"success": True, "errors": [], "warnings": [], "raw_output": "{}"}
        with patch(
            "uipath_claude.validation.activity_validator.validate_activities_in_xaml"
        ) as mock_validate_activities:
            mock_validate_activities.return_value = (
                False,
                ["Activity 'FakeHallucinatedActivity' not found in UiPath packages."],
            )

            result = validate_generated_project(root)

    assert result["success"] is False
    assert len(result["errors"]) == 1
    assert "FakeHallucinatedActivity" in result["errors"][0]


def test_materialize_adds_mail_dependency_when_mail_types_used(tmp_path: Path) -> None:
    root = tmp_path / "mail-project"
    root.mkdir()
    (root / "project.json").write_text(
        json.dumps(
            {
                "name": "MailProject",
                "dependencies": {"UiPath.System.Activities": "[24.10.6]"},
            }
        ),
        encoding="utf-8",
    )
    text = """
<<<UIPATH_FILE path="Main.xaml">>>
<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities"
 xmlns:snm="clr-namespace:System.Net.Mail;assembly=System.Net.Mail">
  <Sequence>
    <ui:GetOutlookMailMessages />
    <ui:ForEach x:TypeArguments="snm:MailMessage" />
  </Sequence>
</Activity>
<<<END_UIPATH_FILE>>>
"""
    materialize_from_assistant_text(text, output_root=root, allow_project_files=True)
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert "UiPath.Mail.Activities" in project["dependencies"]


def test_materialize_adds_integration_service_dependency_when_uip_used(tmp_path: Path) -> None:
    root = tmp_path / "is-project"
    root.mkdir()
    (root / "project.json").write_text(
        json.dumps(
            {
                "name": "ISProject",
                "dependencies": {"UiPath.System.Activities": "[24.10.6]"},
            }
        ),
        encoding="utf-8",
    )
    text = """
<<<UIPATH_FILE path="Main.xaml">>>
<Activity xmlns:uip="clr-namespace:UiPath.IntegrationService.Activities;assembly=UiPath.IntegrationService.Activities"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence>
    <uip:InvokeConnection />
  </Sequence>
</Activity>
<<<END_UIPATH_FILE>>>
"""
    materialize_from_assistant_text(text, output_root=root, allow_project_files=True)
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert "UiPath.IntegrationService.Activities" in project["dependencies"]
