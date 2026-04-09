"""Test bootstrap flow."""
from unittest.mock import AsyncMock, patch
from uipath_claude.query.bootstrap import run_bootstrap_flow


@patch("uipath_claude.agents.ba.BAAgent")
@patch("uipath_claude.agents.sa.SAAgent")
@patch("uipath_claude.agents.developer.DeveloperAgent")
@patch("uipath_claude.agents.qa.QAAgent")
async def test_run_bootstrap_flow(mock_qa, mock_dev, mock_sa, mock_ba):
    """Test running bootstrap flow."""
    mock_ba_instance = AsyncMock()
    mock_ba_instance.run = AsyncMock(return_value="PDD content")
    mock_ba.return_value = mock_ba_instance
    
    mock_sa_instance = AsyncMock()
    mock_sa_instance.run = AsyncMock(return_value="SDD content")
    mock_sa.return_value = mock_sa_instance
    
    mock_dev_instance = AsyncMock()
    mock_dev_instance.run = AsyncMock(return_value="Code content")
    mock_dev.return_value = mock_dev_instance
    
    mock_qa_instance = AsyncMock()
    mock_qa_instance.run = AsyncMock(return_value="Validation content")
    mock_qa.return_value = mock_qa_instance
    
    result = await run_bootstrap_flow("Create a workflow")
    
    assert "pdd" in result
    assert "sdd" in result
    assert "code" in result
    assert "validation" in result
