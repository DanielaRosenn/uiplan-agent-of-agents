"""Test environment detection."""
from uipath_claude.context.environment import get_environment_info


def test_get_environment_info():
    """Test environment info collection."""
    env_info = get_environment_info()
    
    assert "python_version" in env_info
    assert "platform" in env_info
    assert "cwd" in env_info
    assert env_info["python_version"].startswith("3.")
