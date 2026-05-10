"""Integration test for bootstrap flow."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from uipath_claude.cli.app import app


runner = CliRunner()


@pytest.mark.integration
@patch("uipath_claude.cli.app.run_bootstrap_flow", new_callable=AsyncMock)
@patch("uipath_claude.query.engine_factory.create_conversation_engine_from_env")
def test_start_project_command(mock_engine, mock_bootstrap):
    """start-project runs bootstrap without live Bedrock when bootstrap flow is mocked."""
    mock_engine.return_value = MagicMock()
    mock_bootstrap.return_value = {"paths": {"pdd": "/tmp/p.md"}}
    result = runner.invoke(app, ["start-project", "TestProject"])
    assert result.exit_code == 0
    assert "bootstrap complete" in result.stdout.lower()
    mock_bootstrap.assert_awaited_once()
