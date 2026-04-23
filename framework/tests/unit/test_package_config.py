"""Test package configuration."""
import tomli
from pathlib import Path


def test_pyproject_toml_has_correct_package_name():
    """Test pyproject.toml has correct package name."""
    pyproject_path = Path(__file__).resolve().parents[3] / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        config = tomli.load(f)
    
    assert config["project"]["name"] == "uipath-claude-code"


def test_pyproject_toml_has_correct_entry_point():
    """Test pyproject.toml has correct CLI entry point."""
    pyproject_path = Path(__file__).resolve().parents[3] / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        config = tomli.load(f)
    
    scripts = config["project"]["scripts"]
    assert "uipath-claude" in scripts
    assert scripts["uipath-claude"] == "uipath_claude.cli.app:app"
