"""Tests for skill execution tools."""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uipath_claude.tools.skill_execution_tools import (
    read_file,
    write_file,
    list_directory,
    read_project_json,
    install_package,
    validate_file,
    run_uip_command,
    find_activity_info,
    ensure_project_structure,
    get_skill_execution_tools,
)


class TestReadFile:
    """Tests for read_file tool."""

    def test_read_existing_file(self, tmp_path, monkeypatch):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = read_file.invoke({"file_path": str(test_file)})
        assert result.startswith("[OK]")
        assert "Hello, World!" in result

    def test_read_nonexistent_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = read_file.invoke({"file_path": str(tmp_path / "nonexistent.txt")})
        assert "Error: File not found" in result

    def test_read_large_file_truncated(self, tmp_path, monkeypatch):
        test_file = tmp_path / "large.txt"
        test_file.write_text("x" * 100000)
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = read_file.invoke({"file_path": str(test_file)})
        assert "TRUNCATED" in result


class TestWriteFile:
    """Tests for write_file tool."""

    def test_write_new_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "test-session")
        
        result = write_file.invoke({
            "file_path": "output.txt",
            "content": "Test content",
        })
        
        assert "Successfully wrote" in result
        written = tmp_path / "test-session" / "output.txt"
        assert written.exists()
        assert written.read_text() == "Test content"

    def test_write_creates_parent_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "test-session")
        
        result = write_file.invoke({
            "file_path": "subdir/nested/file.txt",
            "content": "Nested content",
        })
        
        assert "Successfully wrote" in result
        written = tmp_path / "test-session" / "subdir" / "nested" / "file.txt"
        assert written.exists()

    def test_write_rejects_path_traversal(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "test-session")
        
        result = write_file.invoke({
            "file_path": "../escape.txt",
            "content": "Bad content",
        })
        
        assert "Error: Invalid file path" in result

    def test_write_refuses_project_json_without_flag(self, tmp_path, monkeypatch):
        # Scaffold guard: project.json must go through create_project, never
        # write_file, to avoid Studio dependency mismatches.
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "test-session")

        result = write_file.invoke({
            "file_path": "project.json",
            "content": "{}",
        })

        assert "Refusing to write 'project.json'" in result
        assert "create_project" in result

    def test_first_coded_workflow_blocked_without_justification(
        self, tmp_path, monkeypatch
    ):
        # Activities-first soft-block: first CodedWorkflow .cs in a XAML
        # project requires an explicit justification.
        (tmp_path / "project.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")

        result = write_file.invoke({
            "file_path": "Process.cs",
            "content": "public class Process : CodedWorkflow {}",
        })

        assert result.startswith("[ERROR]")
        assert "Activities-first policy" in result
        assert "justification" in result
        assert not (tmp_path / "Process.cs").exists()

    def test_first_coded_workflow_allowed_with_justification(
        self, tmp_path, monkeypatch
    ):
        (tmp_path / "project.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")

        result = write_file.invoke({
            "file_path": "Process.cs",
            "content": "public class Process : CodedWorkflow {}",
            "justification": "rule 3: SDK call with no equivalent activity",
        })

        assert "Successfully wrote" in result
        assert (tmp_path / "Process.cs").exists()

    def test_second_coded_workflow_not_blocked(self, tmp_path, monkeypatch):
        # Guard fires only on the FIRST coded workflow in the project.
        (tmp_path / "project.json").write_text("{}")
        (tmp_path / "Existing.cs").write_text(
            "public class Existing : CodedWorkflow {}"
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")

        result = write_file.invoke({
            "file_path": "Second.cs",
            "content": "public class Second : CodedWorkflow {}",
        })

        assert "Successfully wrote" in result
        assert (tmp_path / "Second.cs").exists()

    def test_xaml_write_not_blocked_by_activities_guard(
        self, tmp_path, monkeypatch
    ):
        (tmp_path / "project.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")

        xaml = (
            '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" />'
        )
        result = write_file.invoke({
            "file_path": "Main.xaml",
            "content": xaml,
        })

        assert "Successfully wrote" in result
        assert "Activities-first" not in result
        assert (tmp_path / "Main.xaml").exists()


class TestListDirectory:
    """Tests for list_directory tool."""

    def test_list_files(self, tmp_path, monkeypatch):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "c.xml").write_text("c")
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = list_directory.invoke({"dir_path": str(tmp_path), "pattern": "*.txt"})
        
        assert "a.txt" in result
        assert "b.txt" in result
        assert "c.xml" not in result

    def test_list_nonexistent_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = list_directory.invoke({"dir_path": str(tmp_path / "nodir")})
        assert "Error: Directory not found" in result


class TestReadProjectJson:
    """Tests for read_project_json tool."""

    def test_read_valid_project_json(self, tmp_path, monkeypatch):
        project = {
            "name": "TestProject",
            "dependencies": {"UiPath.System.Activities": "[26.2.4]"},
            "entryPoints": [{"filePath": "Main.xaml"}],
            "expressionLanguage": "VisualBasic",
        }
        (tmp_path / "project.json").write_text(json.dumps(project))
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = read_project_json.invoke({"project_dir": str(tmp_path)})
        raw = result.removeprefix("[OK]").lstrip().removeprefix(":").lstrip()
        parsed = json.loads(raw)
        
        assert parsed["name"] == "TestProject"
        assert "UiPath.System.Activities" in parsed["dependencies"]

    def test_read_missing_project_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = read_project_json.invoke({"project_dir": str(tmp_path)})
        assert "Error: project.json not found" in result


class TestInstallPackage:
    """Tests for install_package tool."""

    def test_install_missing_project_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = install_package.invoke({
            "project_dir": str(tmp_path),
            "package_id": "UiPath.Mail.Activities",
        })
        
        assert "Error: No project.json found" in result

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_install_success(self, mock_run, tmp_path, monkeypatch):
        (tmp_path / "project.json").write_text('{"dependencies": {}}')
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"Result": "Success"}',
            stderr="",
        )
        
        result = install_package.invoke({
            "project_dir": str(tmp_path),
            "package_id": "UiPath.Mail.Activities",
            "version": "2.5.10",
        })
        
        assert "Successfully installed" in result


class TestValidateFile:
    """Tests for validate_file tool."""

    @patch("uipath_claude.tools.skill_execution_tools.run_uip_rpa_get_errors")
    def test_validate_success(self, mock_validate, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        mock_validate.return_value = {
            "success": True,
            "errors": [],
            "warnings": [],
            "raw_output": "",
            "studio_required": False,
        }
        
        result = validate_file.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml",
        })
        
        assert "Validation passed" in result

    @patch("uipath_claude.tools.skill_execution_tools.run_uip_rpa_get_errors")
    def test_validate_failure(self, mock_validate, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        mock_validate.return_value = {
            "success": False,
            "errors": ["Missing xmlns:ui declaration"],
            "warnings": [],
            "raw_output": "",
            "studio_required": False,
        }
        
        result = validate_file.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml",
        })
        
        assert "Validation failed" in result
        assert "Missing xmlns:ui" in result


class TestRunUipCommand:
    """Tests for run_uip_command tool."""

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_find_activities(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"Result": "Success", "Data": {"activities": []}}',
            stderr="",
        )
        
        # Call the underlying function directly since LangChain tool wrapper
        # has issues with list arguments
        from uipath_claude.tools.skill_execution_tools import run_uip_command
        result = run_uip_command.func(
            command="rpa",
            command_args=["find-activities", "--query", "Outlook", "--output", "json"],
        )
        
        assert "activities" in result

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_strips_use_studio_flag(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"Result": "Success", "Data": {"ok": true}}',
            stderr="",
        )

        from uipath_claude.tools.skill_execution_tools import run_uip_command

        result = run_uip_command.func(
            command="rpa",
            command_args=[
                "find-activities",
                "--use-studio",
                "--query",
                "X",
                "--output",
                "json",
            ],
        )

        cmd = mock_run.call_args[0][0]
        assert "--use-studio" not in cmd
        assert "find-activities" in cmd
        assert "removed unsupported uip flag" in result.lower()
        assert "--use-studio" in result


class TestFindActivityInfo:
    """Tests for find_activity_info tool."""

    def test_find_from_local_docs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        # Create mock local docs
        docs_dir = tmp_path / ".local" / "docs" / "packages" / "UiPath.Mail.Activities"
        docs_dir.mkdir(parents=True)
        (docs_dir / "GetOutlookMailMessages.md").write_text(
            "# GetOutlookMailMessages\nReads emails from Outlook inbox."
        )
        
        result = find_activity_info.invoke({
            "query": "GetOutlookMailMessages",
            "project_dir": str(tmp_path),
        })
        
        assert result.startswith("[OK]")
        assert "GetOutlookMailMessages" in result
        assert "bundled_docs" in result or "UiPath.Mail.Activities" in result


class TestEnsureProjectStructure:
    """Tests for ensure_project_structure tool."""

    def test_missing_project_json_routes_to_create_project(self, tmp_path, monkeypatch):
        # ensure_project_structure no longer hand-writes a minimal project.json
        # because that caused multi-major dependency mismatches against Studio.
        # When project.json is absent it now refuses and routes the caller at
        # create_project (which wraps `uip rpa create-project`).
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "test-session")

        result = ensure_project_structure.invoke({"project_dir": "."})

        assert result.startswith("[ERROR]")
        assert "No project.json at" in result
        assert "create_project" in result
        project_json = tmp_path / "test-session" / "project.json"
        assert not project_json.exists()

    def test_existing_project_json_unchanged(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "existing"
        project_dir.mkdir()
        project_json = project_dir / "project.json"
        project_json.write_text('{"name": "Existing"}')
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = ensure_project_structure.invoke({"project_dir": str(project_dir)})
        
        assert "Project structure OK" in result
        assert json.loads(project_json.read_text())["name"] == "Existing"


class TestGetSkillExecutionTools:
    """Tests for get_skill_execution_tools function."""

    def test_returns_all_tools(self):
        tools = get_skill_execution_tools()
        
        tool_names = {t.name for t in tools}
        expected = {
            "read_file",
            "write_file",
            "list_directory",
            "read_project_json",
            "install_package",
            "validate_file",
            "run_uip_command",
            "find_activity_info",
            "validate_and_fix_loop",
            "debug_workflow",
            "ensure_project_structure",
        }
        
        assert expected.issubset(tool_names)
