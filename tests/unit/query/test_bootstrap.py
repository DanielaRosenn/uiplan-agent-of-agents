"""Test bootstrap flow."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uipath_claude.query.bootstrap import run_bootstrap_flow


@pytest.mark.asyncio
async def test_run_bootstrap_flow_writes_artifacts(tmp_path):
    """Bootstrap invokes LLM helper and writes artifact files."""
    engine = MagicMock()

    with patch(
        "uipath_claude.query.bootstrap.invoke_agent_llm",
        new=AsyncMock(
            side_effect=[
                "PDD content",
                "SDD content",
                "Code content",
                "Validation content",
            ],
        ),
    ):
        result = await run_bootstrap_flow(
            "Create a workflow",
            engine=engine,
            output_root=tmp_path,
        )

    assert result["pdd"] == "PDD content"
    assert result["validation"] == "Validation content"
    paths = result["paths"]
    assert paths["pdd"].endswith("-pdd.md")
    assert paths["sdd"].endswith("-sdd.md")
    assert paths["qa"].endswith("-validation.md")
    assert "implementation_plan" in paths
    assert (tmp_path / "docs" / "pdd").exists()
