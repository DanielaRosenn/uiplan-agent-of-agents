import re
from pathlib import Path

import pytest

_MERMAID_FENCE = re.compile(r"```mermaid", re.IGNORECASE)


def _count_mermaid(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(_MERMAID_FENCE.findall(text))


def test_uiplan_kit_contains_required_templates():
    root = Path(__file__).resolve().parents[3]
    kit = root / "docs" / "uiplan" / "kit"
    required = [
        "_spec-template.md",
        "_plan-template.md",
        "_tasks-template.md",
        "_diagram-patterns.md",
        "README.md",
    ]
    assert all((kit / name).is_file() for name in required)


def test_kit_templates_meet_minimum_mermaid_counts():
    root = Path(__file__).resolve().parents[3]
    kit = root / "docs" / "uiplan" / "kit"
    assert _count_mermaid(kit / "_spec-template.md") >= 2
    assert _count_mermaid(kit / "_plan-template.md") >= 2
    assert _count_mermaid(kit / "_tasks-template.md") >= 1


@pytest.mark.parametrize(
    "name,min_blocks",
    [
        ("_spec-template.md", 2),
        ("_plan-template.md", 2),
        ("_tasks-template.md", 1),
    ],
)
def test_kit_templates_pass_visual_density(name: str, min_blocks: int) -> None:
    root = Path(__file__).resolve().parents[3]
    kit = root / "docs" / "uiplan" / "kit"
    text = (kit / name).read_text(encoding="utf-8")
    bodies = re.findall(
        r"```mermaid\s*\n(.*?)```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    assert len(bodies) >= min_blocks
    for body in bodies:
        assert "classDef" in body
        lowered = body.lower()
        is_seq = "sequencediagram" in lowered
        is_state = "statediagram" in lowered
        if not is_seq and not is_state:
            assert "linkStyle" in body
