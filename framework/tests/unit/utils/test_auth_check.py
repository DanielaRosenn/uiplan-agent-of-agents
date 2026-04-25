"""Tests for auth_check helpers."""
from io import StringIO

import pytest
from rich.console import Console

from uipath_claude.utils import auth_check


def test_resolve_uipath_auth_argv_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "UIPATH_ORCHESTRATOR_URL",
        "https://cloud.uipath.com/org/t/orchestrator_",
    )
    monkeypatch.setenv("UIPATH_TENANT_NAME", "mytenant")
    argv, err = auth_check.resolve_uipath_auth_argv()
    assert err is None
    assert argv == ["uipath", "auth", "--cloud", "--tenant", "mytenant"]


def test_resolve_uipath_auth_argv_onprem(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UIPATH_ORCHESTRATOR_URL", "https://orch.example.com/t/orchestrator_")
    monkeypatch.setenv("UIPATH_TENANT_NAME", "t1")
    argv, err = auth_check.resolve_uipath_auth_argv()
    assert err is None
    assert argv[:3] == ["uipath", "auth", "--base-url"]
    assert "https://orch.example.com/t/orchestrator_" in argv
    assert argv[-2:] == ["--tenant", "t1"]


def test_resolve_uipath_auth_argv_tenant_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UIPATH_ORCHESTRATOR_URL", raising=False)
    monkeypatch.setenv("UIPATH_TENANT_NAME", "solo")
    argv, err = auth_check.resolve_uipath_auth_argv()
    assert err is None
    assert argv == ["uipath", "auth", "--cloud", "--tenant", "solo"]


def test_resolve_uipath_auth_argv_missing_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UIPATH_TENANT_NAME", raising=False)
    argv, err = auth_check.resolve_uipath_auth_argv()
    assert argv is None
    assert err and "UIPATH_TENANT_NAME" in err


def test_prompt_for_authentication_uses_ascii_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows terminals may use cp1252, so startup auth text must be ASCII-safe."""
    output = StringIO()
    console = Console(file=output, force_terminal=False, color_system=None)
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *args, **kwargs: "2")

    choice = auth_check.prompt_for_authentication(console)

    rendered = output.getvalue()
    assert choice == "skip_auth"
    assert "! UiPath CLI Authentication Required" in rendered
    assert "\u26a0" not in rendered
