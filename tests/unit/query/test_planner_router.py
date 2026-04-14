"""Tests for planner routing heuristics."""

import pytest

from uipath_claude.query.planner_router import (
    find_planner_skill,
    get_planner_skill_name,
    should_use_planner,
)


def test_should_use_planner_low_confidence():
    use, reason = should_use_planner("do something", 50)
    assert use is True
    assert reason == "low_confidence"


def test_low_confidence_requires_minimum_signal():
    use, _reason = should_use_planner("hello there", 0)
    assert use is False


def test_should_not_use_planner_high_confidence():
    use, reason = should_use_planner("create xaml workflow", 85)
    assert use is False
    assert reason == "clear_request"


def test_should_use_planner_multi_skill():
    use, reason = should_use_planner("build and deploy to orchestrator", 90)
    assert use is True
    assert reason == "multi_skill"


def test_should_use_planner_exploration():
    use, reason = should_use_planner("what can I build?", 80)
    assert use is True
    assert reason == "exploration"


def test_exploration_with_specialist_surface_skips_planner_when_confident():
    use, reason = should_use_planner("help me build an outlook workflow", 85)
    assert use is False
    assert reason == "clear_request"


def test_get_planner_skill_name():
    assert get_planner_skill_name() == "uipath-planner"


def test_find_planner_skill():
    skills = [
        {"name": "uipath-rpa", "path": "/a"},
        {"name": "uipath-planner", "path": "/p"},
    ]
    found = find_planner_skill(skills)
    assert found is not None
    assert found["name"] == "uipath-planner"


def test_find_planner_skill_missing():
    assert find_planner_skill([{"name": "uipath-rpa"}]) is None
