"""Tests for ValidationPipeline."""

from pathlib import Path
from unittest.mock import patch

import pytest

from uipath_claude.validation.pipeline import ValidationPipeline


@pytest.fixture
def validation_pipeline() -> ValidationPipeline:
    return ValidationPipeline()


def test_error_categorization(validation_pipeline: ValidationPipeline) -> None:
    assert validation_pipeline._categorize_error("package not found") == "package"
    assert validation_pipeline._categorize_error("type mismatch on assign") == "type"
    assert validation_pipeline._categorize_error("activity property invalid") == "activity"


def test_structural_check_detects_outlook_result(
    validation_pipeline: ValidationPipeline, tmp_path: Path
) -> None:
    xaml = tmp_path / "Main.xaml"
    xaml.write_text("<Activity>GetOutlookMailMessages.Result</Activity>")
    result = validation_pipeline._run_structural_checks(tmp_path, xaml)
    assert not result.valid
    assert any("Messages attribute" in e.message for e in result.errors)


def test_validation_skips_studio_without_project_json(
    validation_pipeline: ValidationPipeline, tmp_path: Path
) -> None:
    xaml = tmp_path / "Main.xaml"
    xaml.write_text(
        '<Activity x:Class="Workflow.Main" '
        'xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
        "<Sequence /></Activity>"
    )
    with patch(
        "uipath_claude.validation.activity_validator.validate_activities_in_xaml",
        return_value=(True, []),
    ):
        result = validation_pipeline.validate(tmp_path)
    assert result.valid
    assert not result.studio_ran
    assert any("No project.json" in w.message for w in result.warnings)
