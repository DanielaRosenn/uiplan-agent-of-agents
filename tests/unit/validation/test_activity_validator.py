"""Test activity validator."""
from unittest.mock import MagicMock, patch

import pytest

from uipath_claude.validation.activity_validator import (
    extract_activity_names_from_xaml,
    validate_activities_in_xaml,
)


SAMPLE_XAML = """<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010" x:Class="Main"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:ui="http://schemas.uipath.com/workflow/activities">
  <Sequence>
    <ui:LogMessage DisplayName="Log Message" Message="Hello" />
    <ui:StartOutlook DisplayName="Start Outlook" />
    <ui:GetOutlookNamespace DisplayName="Get Namespace" />
  </Sequence>
</Activity>
"""


def test_extract_activity_names_from_xaml():
    """Test extracting activity names from XAML."""
    activities = extract_activity_names_from_xaml(SAMPLE_XAML)
    
    assert "ui:LogMessage" in activities
    assert "ui:StartOutlook" in activities
    assert "ui:GetOutlookNamespace" in activities
    assert len(activities) == 3


def test_extract_activity_names_empty_xaml():
    """Test extracting from empty XAML."""
    activities = extract_activity_names_from_xaml("")
    assert activities == []


def test_extract_activity_names_no_activities():
    """Test extracting from XAML with no activities."""
    xaml = """<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
</Activity>
"""
    activities = extract_activity_names_from_xaml(xaml)
    assert activities == []


@patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities")
def test_validate_activities_all_valid(mock_find):
    """Test validation when all activities exist."""
    mock_find.return_value = {
        "success": True,
        "found": ["ui:LogMessage", "ui:StartOutlook"],
        "not_found": [],
    }
    
    result = validate_activities_in_xaml(
        SAMPLE_XAML,
        project_path="/test/project"
    )
    
    assert result["success"] is True
    assert len(result["not_found"]) == 0
    mock_find.assert_called_once()


@patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities")
def test_validate_activities_some_invalid(mock_find):
    """Test validation when some activities don't exist."""
    mock_find.return_value = {
        "success": True,
        "found": ["ui:LogMessage"],
        "not_found": ["ui:StartOutlook", "ui:GetOutlookNamespace"],
    }
    
    result = validate_activities_in_xaml(
        SAMPLE_XAML,
        project_path="/test/project"
    )
    
    assert result["success"] is False
    assert "ui:StartOutlook" in result["not_found"]
    assert "ui:GetOutlookNamespace" in result["not_found"]


@patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities")
def test_validate_activities_cli_error(mock_find):
    """Test validation when CLI command fails."""
    mock_find.return_value = {
        "success": False,
        "error": "uip CLI not found",
        "found": [],
        "not_found": [],
    }
    
    result = validate_activities_in_xaml(
        SAMPLE_XAML,
        project_path="/test/project"
    )
    
    assert result["success"] is False
    assert "error" in result
    assert "uip CLI not found" in result["error"]


def test_validate_activities_empty_xaml():
    """Test validation with empty XAML."""
    result = validate_activities_in_xaml("", project_path="/test/project")
    
    assert result["success"] is True
    assert result["not_found"] == []
