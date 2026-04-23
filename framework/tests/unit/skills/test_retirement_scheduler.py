"""Scheduled retirement runs at most once per interval."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from uipath_claude.skills.insights import InsightType, SkillInsight, SkillInsightsFile
from uipath_claude.skills.retirement_scheduler import maybe_run_retirement_scheduled


def _low_conf_file() -> SkillInsightsFile:
    return SkillInsightsFile(
        skill_name="uipath-automation",
        insights=[
            SkillInsight(
                skill_name="uipath-automation",
                insight_type=InsightType.FAILURE_PATTERN,
                content="Noisy low confidence",
                success_count=0,
                failure_count=5,
            ),
        ],
    )


def _project_layout(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / ".uipath-claude" / "skill-insights").mkdir(parents=True)
    return proj


def test_retirement_skipped_within_interval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = _project_layout(tmp_path)
    marker = proj / ".uipath-claude" / ".retirement_at"
    marker.write_text(str(int(time.time())), encoding="utf-8")

    fpath = proj / ".uipath-claude" / "skill-insights" / "uipath-automation.json"
    fpath.write_text(json.dumps(_low_conf_file().to_dict(), indent=2), encoding="utf-8")

    monkeypatch.chdir(proj)
    maybe_run_retirement_scheduled()
    after = json.loads(fpath.read_text(encoding="utf-8"))
    assert len(after["insights"]) == 1


def test_retirement_runs_when_marker_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = _project_layout(tmp_path)
    marker = proj / ".uipath-claude" / ".retirement_at"
    marker.write_text(str(int(time.time()) - 48 * 3600), encoding="utf-8")

    fpath = proj / ".uipath-claude" / "skill-insights" / "uipath-automation.json"
    fpath.write_text(json.dumps(_low_conf_file().to_dict(), indent=2), encoding="utf-8")

    monkeypatch.chdir(proj)
    maybe_run_retirement_scheduled()
    after = json.loads(fpath.read_text(encoding="utf-8"))
    assert after["insights"] == []
    assert int(marker.read_text(encoding="utf-8").strip()) > 0


def test_respects_uipath_skip_retirement_schedule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UIPATH_SKIP_RETIREMENT_SCHEDULE", "1")
    proj = _project_layout(tmp_path)
    marker = proj / ".uipath-claude" / ".retirement_at"
    marker.write_text("0", encoding="utf-8")

    fpath = proj / ".uipath-claude" / "skill-insights" / "x.json"
    fpath.write_text(json.dumps(_low_conf_file().to_dict(), indent=2), encoding="utf-8")
    monkeypatch.chdir(proj)

    maybe_run_retirement_scheduled()

    after = json.loads(fpath.read_text(encoding="utf-8"))
    assert len(after["insights"]) == 1
    assert marker.read_text(encoding="utf-8") == "0"


def test_corrupt_marker_treated_as_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = _project_layout(tmp_path)
    marker = proj / ".uipath-claude" / ".retirement_at"
    marker.write_text("not-a-number", encoding="utf-8")

    fpath = proj / ".uipath-claude" / "skill-insights" / "a.json"
    fpath.write_text(json.dumps(_low_conf_file().to_dict(), indent=2), encoding="utf-8")
    monkeypatch.chdir(proj)

    maybe_run_retirement_scheduled()
    assert json.loads(fpath.read_text(encoding="utf-8"))["insights"] == []
    assert marker.read_text(encoding="utf-8").strip().isdigit()


def test_partial_failure_does_not_advance_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = _project_layout(tmp_path)
    marker = proj / ".uipath-claude" / ".retirement_at"
    marker.write_text("0", encoding="utf-8")

    good = proj / ".uipath-claude" / "skill-insights" / "good.json"
    good.write_text(json.dumps(_low_conf_file().to_dict(), indent=2), encoding="utf-8")
    bad = proj / ".uipath-claude" / "skill-insights" / "bad.json"
    bad.write_text("{not json", encoding="utf-8")

    monkeypatch.chdir(proj)
    maybe_run_retirement_scheduled()

    assert marker.read_text(encoding="utf-8") == "0"
    assert json.loads(good.read_text(encoding="utf-8"))["insights"] == []
    assert "not json" in bad.read_text(encoding="utf-8")


def test_uipath_project_root_overrides_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = _project_layout(tmp_path)
    marker = proj / ".uipath-claude" / ".retirement_at"
    marker.write_text("0", encoding="utf-8")
    fpath = proj / ".uipath-claude" / "skill-insights" / "a.json"
    fpath.write_text(json.dumps(_low_conf_file().to_dict(), indent=2), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_PROJECT_ROOT", str(proj))
    maybe_run_retirement_scheduled()

    assert json.loads(fpath.read_text(encoding="utf-8"))["insights"] == []
