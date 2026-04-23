"""Test UiPath project detection."""
import json
from pathlib import Path
from uipath_claude.context.project import detect_uipath_project, UiPathProjectContext


def test_detect_uipath_project_with_project_json(tmp_path):
    """Test detection with project.json."""
    project_json = tmp_path / "project.json"
    project_json.write_text(json.dumps({
        "name": "TestProject",
        "projectType": "Process",
        "dependencies": {
            "UiPath.System.Activities": "[23.10.0]"
        }
    }))
    
    context = detect_uipath_project(str(tmp_path))
    
    assert context is not None
    assert context["project_name"] == "TestProject"
    assert context["project_type"] == "Process"
    assert context["has_project_json"] is True
    assert "UiPath.System.Activities" in context["dependencies"]


def test_detect_uipath_project_no_project(tmp_path):
    """Test detection returns None when no project found."""
    context = detect_uipath_project(str(tmp_path))
    assert context is None
