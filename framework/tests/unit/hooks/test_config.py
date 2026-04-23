"""Test hook configuration."""
from pathlib import Path
from uipath_claude.hooks.config import load_hooks_config


def test_load_hooks_config(tmp_path):
    """Test loading hooks configuration."""
    hooks_file = tmp_path / ".uipath-claude" / "hooks.json"
    hooks_file.parent.mkdir(parents=True)
    hooks_file.write_text('''{
        "session_start": ["echo 'Session started'"],
        "pre_tool_use": ["echo 'Using tool'"]
    }''')
    
    config = load_hooks_config(str(tmp_path))
    
    assert "session_start" in config
    assert "pre_tool_use" in config
    assert config["session_start"] == ["echo 'Session started'"]


def test_load_hooks_config_no_file():
    """Test loading hooks when no config exists."""
    config = load_hooks_config("/nonexistent")
    assert config == {}
