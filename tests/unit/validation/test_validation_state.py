"""Tests for validation state contract."""

from uipath_claude.validation.state import ValidationState


def test_validation_state_defaults():
    """ValidationState should have predictable default values."""
    state = ValidationState()

    assert state.success is False
    assert state.errors == []
    assert state.warnings == []
    assert state.project_path == ""
