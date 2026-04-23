"""Integration Service smoke helper tests."""
from unittest.mock import MagicMock, patch

from uipath_claude.tools.uipath.integration_service import (
    run_integration_service_connector_check,
)


def test_integration_service_success_first_candidate():
    """Return OK when first CLI command succeeds with output."""
    proc = MagicMock(returncode=0, stdout="connections: []\n", stderr="")
    with patch("subprocess.run", return_value=proc) as mock_run:
        out = run_integration_service_connector_check()
        assert "OK" in out
        assert "connections" in out
        mock_run.assert_called()


def test_integration_service_file_not_found():
    """Clear message when uipath binary is missing."""
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        out = run_integration_service_connector_check()
        assert "not found" in out.lower()
