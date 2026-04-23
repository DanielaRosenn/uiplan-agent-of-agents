"""Tests for CLI manager utilities."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from uipath_claude.tools.cli_manager import (
    get_uip_version,
    install_uip_cli,
    is_uip_installed,
    prompt_install_cli,
)


class TestIsUipInstalled:
    """Tests for is_uip_installed function."""

    def test_returns_true_when_uip_found(self):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/uip" if cmd == "uip" else None
            assert is_uip_installed() is True

    def test_returns_true_when_uip_cmd_found(self):
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "C:\\uip.cmd" if cmd == "uip.cmd" else None
            assert is_uip_installed() is True

    def test_returns_false_when_not_found(self):
        with patch("shutil.which", return_value=None):
            assert is_uip_installed() is False


class TestGetUipVersion:
    """Tests for get_uip_version function."""

    def test_returns_none_when_not_installed(self):
        with patch("uipath_claude.tools.cli_manager.is_uip_installed", return_value=False):
            assert get_uip_version() is None

    def test_returns_version_string_on_success(self):
        with patch("uipath_claude.tools.cli_manager.is_uip_installed", return_value=True):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "1.2.3\n"
            with patch("subprocess.run", return_value=mock_result):
                assert get_uip_version() == "1.2.3"

    def test_returns_none_on_nonzero_exit(self):
        with patch("uipath_claude.tools.cli_manager.is_uip_installed", return_value=True):
            mock_result = MagicMock()
            mock_result.returncode = 1
            with patch("subprocess.run", return_value=mock_result):
                assert get_uip_version() is None

    def test_returns_none_on_exception(self):
        with patch("uipath_claude.tools.cli_manager.is_uip_installed", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("uip", 10)):
                assert get_uip_version() is None


class TestInstallUipCli:
    """Tests for install_uip_cli function."""

    def test_returns_success_on_zero_exit(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            success, message = install_uip_cli()
            assert success is True
            assert "successfully" in message

    def test_returns_failure_on_nonzero_exit(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "permission denied"
        with patch("subprocess.run", return_value=mock_result):
            success, message = install_uip_cli()
            assert success is False
            assert "permission denied" in message

    def test_returns_failure_when_npm_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            success, message = install_uip_cli()
            assert success is False
            assert "npm not found" in message

    def test_returns_failure_on_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("npm", 120)):
            success, message = install_uip_cli()
            assert success is False
            assert "timed out" in message

    def test_returns_failure_on_generic_exception(self):
        with patch("subprocess.run", side_effect=OSError("disk full")):
            success, message = install_uip_cli()
            assert success is False
            assert "disk full" in message


class TestPromptInstallCli:
    """Tests for prompt_install_cli function."""

    def test_returns_true_when_already_installed(self):
        with patch("uipath_claude.tools.cli_manager.is_uip_installed", return_value=True):
            assert prompt_install_cli() is True

    def test_prompts_and_installs_on_confirm(self):
        mock_console = MagicMock()
        with patch("uipath_claude.tools.cli_manager.is_uip_installed", return_value=False):
            with patch("uipath_claude.tools.cli_manager.Confirm.ask", return_value=True):
                with patch(
                    "uipath_claude.tools.cli_manager.install_uip_cli",
                    return_value=(True, "installed"),
                ):
                    result = prompt_install_cli(mock_console)
                    assert result is True

    def test_returns_false_when_install_fails(self):
        mock_console = MagicMock()
        with patch("uipath_claude.tools.cli_manager.is_uip_installed", return_value=False):
            with patch("uipath_claude.tools.cli_manager.Confirm.ask", return_value=True):
                with patch(
                    "uipath_claude.tools.cli_manager.install_uip_cli",
                    return_value=(False, "failed"),
                ):
                    result = prompt_install_cli(mock_console)
                    assert result is False

    def test_returns_false_when_user_declines(self):
        mock_console = MagicMock()
        with patch("uipath_claude.tools.cli_manager.is_uip_installed", return_value=False):
            with patch("uipath_claude.tools.cli_manager.Confirm.ask", return_value=False):
                result = prompt_install_cli(mock_console)
                assert result is False
