"""UiPlan template files ship required sections."""
from __future__ import annotations

from pathlib import Path

import pytest

# tests/unit/docs/<this_file> -> parents[3] is repo root
REPO = Path(__file__).resolve().parents[3]
TPL = REPO / "docs" / "plans" / "_uiplan"


@pytest.mark.parametrize(
    "name,patterns",
    [
        ("_spec-template.md", ("User Story", "Functional Requirements", "Success Criteria")),
        ("_plan-template.md", ("Technical Context", "Constitution Check", "Structure Decision")),
        ("_tasks-template.md", ("Phase", "[US1]", "Dependencies")),
    ],
)
def test_uiplan_template_sections(name, patterns):
    text = (TPL / name).read_text(encoding="utf-8")
    for p in patterns:
        assert p in text, f"{name} missing {p!r}"
