# tests/unit/test_project_detector.py
"""Tests for UiPath project detection."""

import pytest
from pathlib import Path

from agent.context.project_detector import detect_uipath_project, UiPathProjectContext


class TestProjectDetector:
    @pytest.fixture
    def sample_project_path(self, tmp_path):
        """Create a sample UiPath project structure."""
        project_json = tmp_path / "project.json"
        project_json.write_text('''{
            "name": "TestRPAProject",
            "projectId": "12345678-1234-1234-1234-123456789012",
            "description": "Test UiPath project",
            "main": "Main.xaml",
            "dependencies": {
                "UiPath.System.Activities": "[25.10.3]"
            },
            "schemaVersion": "4.0",
            "expressionLanguage": "VisualBasic",
            "targetFramework": "Windows"
        }''')
        
        # Create a workflow file
        (tmp_path / "Main.xaml").write_text("<Activity />")
        
        return tmp_path
    
    def test_detects_project_from_project_json(self, sample_project_path):
        """Detects UiPath project from project.json."""
        result = detect_uipath_project(sample_project_path)
        
        assert result is not None
        assert result.name == "TestRPAProject"
        assert result.project_id == "12345678-1234-1234-1234-123456789012"
    
    def test_returns_none_for_non_project_dir(self, tmp_path):
        """Returns None when no UiPath project found."""
        result = detect_uipath_project(tmp_path)
        assert result is None
    
    def test_finds_workflows(self, sample_project_path):
        """Finds .xaml workflow files."""
        result = detect_uipath_project(sample_project_path)
        assert result is not None
        assert "Main.xaml" in result.workflows

    def test_parses_all_project_fields(self, sample_project_path):
        """Parses all fields from project.json."""
        result = detect_uipath_project(sample_project_path)
        
        assert result is not None
        assert result.description == "Test UiPath project"
        assert result.main_workflow == "Main.xaml"
        assert result.schema_version == "4.0"
        assert result.expression_language == "VisualBasic"
        assert result.target_framework == "Windows"
        assert "UiPath.System.Activities" in result.dependencies

    def test_searches_parent_directories(self, tmp_path):
        """Searches parent directories for project.json."""
        # Create project.json in root
        project_json = tmp_path / "project.json"
        project_json.write_text('{"name": "ParentProject", "projectId": "test-id"}')
        
        # Create nested subdirectory
        subdir = tmp_path / "subfolder" / "nested"
        subdir.mkdir(parents=True)
        
        result = detect_uipath_project(subdir)
        
        assert result is not None
        assert result.name == "ParentProject"

    def test_handles_uiproj_file(self, tmp_path):
        """Creates minimal context from .uiproj file."""
        uiproj = tmp_path / "MyProject.uiproj"
        uiproj.write_text("<Project />")
        (tmp_path / "Main.xaml").write_text("<Activity />")
        
        result = detect_uipath_project(tmp_path)
        
        assert result is not None
        assert result.name == "MyProject"
        assert "Main.xaml" in result.workflows

    def test_handles_invalid_json(self, tmp_path):
        """Returns None for invalid JSON in project.json."""
        project_json = tmp_path / "project.json"
        project_json.write_text("{ invalid json }")
        
        result = detect_uipath_project(tmp_path)
        assert result is None

    def test_finds_nested_workflows(self, tmp_path):
        """Finds workflows in subdirectories."""
        project_json = tmp_path / "project.json"
        project_json.write_text('{"name": "Test", "projectId": "id"}')
        
        # Create workflows in subdirectories
        (tmp_path / "Main.xaml").write_text("<Activity />")
        workflows_dir = tmp_path / "Workflows"
        workflows_dir.mkdir()
        (workflows_dir / "SubWorkflow.xaml").write_text("<Activity />")
        
        result = detect_uipath_project(tmp_path)
        
        assert result is not None
        assert len(result.workflows) == 2
        assert "Main.xaml" in result.workflows
        # Check for nested workflow (path separator may vary)
        assert any("SubWorkflow.xaml" in w for w in result.workflows)
