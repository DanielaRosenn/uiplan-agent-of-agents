"""Test activity validator."""
from pathlib import Path
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
    assert isinstance(activities, set)


def test_extract_activity_names_empty_xaml():
    """Test extracting from empty XAML."""
    activities = extract_activity_names_from_xaml("")
    assert activities == set()
    assert isinstance(activities, set)


def test_extract_activity_names_no_activities():
    """Test extracting from XAML with no activities."""
    xaml = """<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
</Activity>
"""
    activities = extract_activity_names_from_xaml(xaml)
    assert activities == set()
    assert isinstance(activities, set)


@patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities")
def test_validate_activities_all_valid(mock_find, tmp_path):
    """Test validation when all activities exist."""
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(SAMPLE_XAML, encoding="utf-8")
    
    mock_find.return_value = {
        "success": True,
        "found": True,
    }
    
    success, invalid = validate_activities_in_xaml(xaml_file)
    
    assert success is True
    assert len(invalid) == 0
    assert mock_find.call_count == 3


@patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities")
def test_validate_activities_some_invalid(mock_find, tmp_path):
    """Test validation when some activities don't exist."""
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(SAMPLE_XAML, encoding="utf-8")
    
    def mock_find_side_effect(query):
        if query == "ui:LogMessage":
            return {"success": True, "found": True}
        else:
            return {"success": True, "found": False}
    
    mock_find.side_effect = mock_find_side_effect
    
    success, invalid = validate_activities_in_xaml(xaml_file)
    
    assert success is False
    assert "ui:StartOutlook" in invalid
    assert "ui:GetOutlookNamespace" in invalid
    assert "ui:LogMessage" not in invalid


@patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities")
def test_validate_activities_cli_error(mock_find, tmp_path):
    """Test validation when CLI command fails."""
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(SAMPLE_XAML, encoding="utf-8")
    
    mock_find.return_value = {
        "success": False,
        "found": False,
        "error": "uip CLI not found",
    }
    
    success, invalid = validate_activities_in_xaml(xaml_file)
    
    assert success is True
    assert len(invalid) == 0


def test_validate_activities_empty_xaml(tmp_path):
    """Test validation with empty XAML."""
    xaml_file = tmp_path / "empty.xaml"
    xaml_file.write_text("", encoding="utf-8")
    
    success, invalid = validate_activities_in_xaml(xaml_file)
    
    assert success is True
    assert invalid == []


def test_validate_activities_skip_validation(tmp_path):
    """Test validation with skip_validation=True."""
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text(SAMPLE_XAML, encoding="utf-8")
    
    success, invalid = validate_activities_in_xaml(xaml_file, skip_validation=True)
    
    assert success is True
    assert invalid == []
