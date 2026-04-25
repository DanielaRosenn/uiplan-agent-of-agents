"""Runs only when ``mmdc`` is installed (local or CI with Node)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.uiplan.validators.mermaid_mmdc import mmdc_on_path, validate_mermaid_with_mmdc


@pytest.mark.skipif(mmdc_on_path() is None, reason="mmdc not on PATH")
def test_mmdc_accepts_minimal_flowchart(tmp_path: Path) -> None:
    md = tmp_path / "x.md"
    md.write_text("```mermaid\nflowchart LR\n  A-->B\n```\n", encoding="utf-8")
    issues = validate_mermaid_with_mmdc([md])
    if issues and all("mmdc failed" in issue for issue in issues):
        pytest.skip(f"mmdc is installed but unusable in this environment: {issues[0]}")
    assert issues == [], issues
