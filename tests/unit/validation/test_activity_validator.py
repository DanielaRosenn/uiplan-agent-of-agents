"""Tests for activity validator."""
import pytest
from pathlib import Path
from unittest.mock import patch

from uipath_claude.validation.activity_validator import (
    extract_activity_names_from_xaml,
    validate_activities_in_xaml,
)


def test_extract_activity_names_finds_ui_activities():
    """Test extracting activity names from XAML."""
    xaml = """
    <Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
        <Sequence>
            <ui:LogMessage Message="test" />
            <ui:GetOutlookMailMessages />
            <ui:ForEach Values="[items]">
                <ui:WriteLine Text="test" />
            </ui:ForEach>
        </Sequence>
    </Activity>
    """
    
    activities = extract_activity_names_from_xaml(xaml)
    
    assert "LogMessage" in activities
    assert "GetOutlookMailMessages" in activities
    assert "ForEach" in activities
    assert "WriteLine" in activities
    # Standard elements should not be included
    assert "Sequence" not in activities
    assert "Activity" not in activities


def test_extract_activity_names_ignores_standard_elements():
    """Test that standard XAML elements are ignored."""
    xaml = """
    <Activity>
        <Sequence>
            <Variable x:TypeArguments="x:String" Name="test" />
            <InArgument x:TypeArguments="x:String" />
        </Sequence>
    </Activity>
    """
    
    activities = extract_activity_names_from_xaml(xaml)
    
    assert "Variable" not in activities
    assert "InArgument" not in activities
    assert "Sequence" not in activities


def test_validate_activities_with_skip_flag(tmp_path):
    """Test validation skips when flag is set."""
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text("<Activity><ui:FakeActivity /></Activity>", encoding='utf-8')
    
    success, errors = validate_activities_in_xaml(xaml_file, skip_validation=True)
    
    assert success is True
    assert len(errors) == 0


def test_validate_activities_handles_missing_file():
    """Test validation handles missing file gracefully."""
    fake_path = Path("/nonexistent/file.xaml")
    
    success, errors = validate_activities_in_xaml(fake_path)
    
    assert success is False
    assert len(errors) == 1
    assert "Failed to read XAML file" in errors[0]


@patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities")
def test_validate_activities_all_valid(mock_find, tmp_path):
    """Test validation when all activities exist."""
    xaml = """
    <Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
        <Sequence>
            <ui:LogMessage Message="test" />
        </Sequence>
    </Activity>
    """
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(xaml, encoding="utf-8")
    
    mock_find.return_value = {
        "success": True,
        "activities": [
            {
                "ClassName": "UiPath.Core.Activities.LogMessage",
                "ActivityTypeId": "LogMessage",
            }
        ],
    }
    
    success, errors = validate_activities_in_xaml(xaml_file)
    
    assert success is True
    assert len(errors) == 0


@patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities")
def test_validate_activities_some_invalid(mock_find, tmp_path):
    """Test validation when some activities don't exist."""
    xaml = """
    <Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
        <Sequence>
            <ui:LogMessage Message="test" />
            <ui:FakeActivity />
        </Sequence>
    </Activity>
    """
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(xaml, encoding="utf-8")
    
    def mock_find_side_effect(query):
        if query == "LogMessage":
            return {
                "success": True,
                "activities": [
                    {
                        "ClassName": "UiPath.Core.Activities.LogMessage",
                        "ActivityTypeId": "LogMessage",
                    }
                ],
            }
        else:
            return {"success": True, "activities": []}
    
    mock_find.side_effect = mock_find_side_effect
    
    success, errors = validate_activities_in_xaml(xaml_file)
    
    assert success is False
    assert len(errors) == 1
    assert "FakeActivity" in errors[0]
    assert "not found in UiPath packages" in errors[0]


@patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities")
def test_validate_activities_cli_error(mock_find, tmp_path):
    """Test validation when CLI command fails."""
    xaml = """
    <Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
        <Sequence>
            <ui:LogMessage Message="test" />
        </Sequence>
    </Activity>
    """
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(xaml, encoding="utf-8")
    
    mock_find.return_value = {
        "success": False,
        "activities": [],
    }
    
    success, errors = validate_activities_in_xaml(xaml_file)
    
    # CLI failure should skip validation for that activity
    assert success is True
    assert len(errors) == 0
