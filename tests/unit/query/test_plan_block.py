from uipath_claude.query.plan_block import (
    PLAN_BLOCK_HEADING,
    build_plan_block,
    contains_plan_block,
)


def test_heading_is_stable_and_used_by_builder_and_detector() -> None:
    assert PLAN_BLOCK_HEADING == "Approved Implementation Plan"
    body = build_plan_block("1. do X\n2. do Y\n")
    assert body.startswith(f"## {PLAN_BLOCK_HEADING}")
    assert "1. do X" in body
    assert contains_plan_block(body) is True
    assert contains_plan_block("no plan here") is False
