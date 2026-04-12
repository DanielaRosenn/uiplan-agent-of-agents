"""Test branding and logo."""
import warnings

import pytest
from rich.panel import Panel
from rich.text import Text

from uipath_claude.rendering.branding import (
    UIPATH_BLUE,
    UIPATH_ORANGE,
    create_welcome_panel,
    get_robot_logo,
    get_version,
    print_welcome_banner,
)


def test_get_version():
    """Test version retrieval returns a string."""
    ver = get_version()
    assert isinstance(ver, str)
    assert len(ver) > 0


def test_get_robot_logo_deprecated():
    """Test robot logo generation emits deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        logo = get_robot_logo()
        
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()
    
    assert isinstance(logo, str)
    assert len(logo) > 0
    assert "UiPath Claude Code" in logo


def test_create_welcome_panel_returns_panel():
    """Test that create_welcome_panel returns a Rich Panel."""
    panel = create_welcome_panel()
    assert isinstance(panel, Panel)


def test_create_welcome_panel_has_title():
    """Test that the panel has a styled title with brand colors."""
    panel = create_welcome_panel()
    assert panel.title is not None
    assert isinstance(panel.title, Text)
    
    title_plain = panel.title.plain
    assert "UiPath" in title_plain
    assert "Claude Code" in title_plain


def test_create_welcome_panel_has_content():
    """Test that the panel contains expected content."""
    panel = create_welcome_panel()
    content = panel.renderable
    assert isinstance(content, Text)
    
    content_plain = content.plain
    assert "Conversational AI for UiPath Automation" in content_plain
    assert "Version:" in content_plain


def test_create_welcome_panel_border_style():
    """Test that the panel has the correct border style."""
    panel = create_welcome_panel()
    assert panel.border_style == "bright_blue"


def test_brand_colors_defined():
    """Test that brand colors are properly defined."""
    assert UIPATH_ORANGE == "#FA4616"
    assert UIPATH_BLUE == "#0067B8"


def test_print_welcome_banner(capsys):
    """Test welcome banner printing does not raise and produces output."""
    print_welcome_banner()
    captured = capsys.readouterr()
    assert "/help" in captured.out
