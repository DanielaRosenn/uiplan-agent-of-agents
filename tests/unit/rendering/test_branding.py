"""Test branding and logo."""
from uipath_claude.rendering.branding import get_robot_logo, print_welcome_banner


def test_get_robot_logo():
    """Test robot logo generation."""
    logo = get_robot_logo()
    assert isinstance(logo, str)
    assert len(logo) > 0


def test_print_welcome_banner():
    """Test welcome banner printing."""
    # Should not raise exception
    print_welcome_banner()
