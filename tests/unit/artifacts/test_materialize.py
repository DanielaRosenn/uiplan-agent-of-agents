"""Tests for materialize_from_assistant_text."""
import sys
from pathlib import Path

from uipath_claude.artifacts.materialize import (
    contains_file_blocks,
    materialize_from_assistant_text,
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
