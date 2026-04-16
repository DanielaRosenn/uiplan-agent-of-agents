"""Ensure the skills updater refreshes only when the cache is stale."""
from __future__ import annotations

from pathlib import Path

import pytest

from uipath_claude.skills import updater


def test_ensure_fresh_no_op_when_recent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        updater,
        "check_for_updates",
        lambda path=None: (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    marker = tmp_path / ".skills_refresh_at"
    marker.write_text("9999999999")
    assert updater.ensure_fresh(marker_path=marker, max_age_seconds=3600) == "skipped: recent"


def test_ensure_fresh_runs_when_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = tmp_path / ".skills_refresh_at"
    marker.write_text("0")

    monkeypatch.setattr(
        updater, "check_for_updates", lambda path=None: (True, "ok", "aaaa", "bbbb")
    )
    monkeypatch.setattr(updater, "update_skills", lambda path=None: (True, "updated"))

    result = updater.ensure_fresh(marker_path=marker, max_age_seconds=3600)
    assert result.startswith("updated")
    assert int(marker.read_text()) > 0


def test_ensure_fresh_offline_is_soft_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = tmp_path / ".skills_refresh_at"
    marker.write_text("0")
    monkeypatch.setattr(
        updater, "check_for_updates", lambda path=None: (False, "offline", None, None)
    )
    result = updater.ensure_fresh(marker_path=marker, max_age_seconds=3600)
    assert "offline" in result or "skipped" in result
