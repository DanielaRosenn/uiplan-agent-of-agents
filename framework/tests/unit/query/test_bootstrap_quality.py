"""Mocked quality rubric: bootstrap stage outputs contain expected structure."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uipath_claude.query.bootstrap import run_bootstrap_flow


@pytest.mark.asyncio
async def test_bootstrap_pdd_rubric_sections(tmp_path):
    """PDD text from mocked LLM should include plan-required headings."""
    pdd = """# Process Definition Document
## Scope
Invoice processing
## Process steps
Read email, extract data
## Exceptions
Outlook unavailable
"""
    sdd = "## Architecture\nUse REFramework\n"
    code = "## Implementation plan\nMain.xaml sequence\n"
    val = "## Validation\nSmoke tests defined\n"

    with patch(
        "uipath_claude.query.bootstrap.invoke_agent_llm",
        new=AsyncMock(side_effect=[pdd, sdd, code, val]),
    ):
        result = await run_bootstrap_flow(
            "Invoices",
            engine=MagicMock(),
            output_root=tmp_path,
        )

    text = result["pdd"].lower()
    for token in ("scope", "process", "exception"):
        assert token in text
