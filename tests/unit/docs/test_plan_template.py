"""Sanity checks for docs/plans/_TEMPLATE.md."""
from __future__ import annotations

from pathlib import Path


def test_plan_template_has_required_sections():
    root = Path(__file__).resolve().parents[3]
    path = root / "docs" / "plans" / "_TEMPLATE.md"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---")
    for needle in (
        "slug:",
        "status:",
        "accepted_at:",
        "accepted_by:",
        "rejection_reason:",
        "published_at:",
        "## Architecture diagram",
        "## Bite-sized tasks",
        "## Verification",
        "## Rollback",
        "```mermaid",
    ):
        assert needle in text
