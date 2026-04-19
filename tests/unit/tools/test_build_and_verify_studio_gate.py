"""Tests for require_studio_debug enforcement when run_after_validate=False (fix #2)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from uipath_claude.tools import skill_execution_tools as set_mod


def _stub_validate(monkeypatch, tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "project.json").write_text("{}")
    main = proj / "Main.xaml"
    main.write_text("<a/>")

    monkeypatch.setattr(
        set_mod,
        "_probe_environment",
        lambda project_dir: {
            "project_dir": project_dir,
            "studio_instances": [],
            "installed_packages": [],
        },
    )
    monkeypatch.setattr(set_mod, "_detect_dependency_mismatches", lambda probe: [])
    monkeypatch.setattr(set_mod, "_resolve_project_path", lambda d: proj)
    monkeypatch.setattr(set_mod, "_discover_workflow_files", lambda d: ["Main.xaml"])
    monkeypatch.setattr(
        set_mod,
        "run_uip_rpa_get_errors",
        lambda *a, **kw: {"success": True, "errors": [], "warnings": []},
    )


def test_require_studio_debug_blocks_when_run_skipped(tmp_path, monkeypatch):
    _stub_validate(monkeypatch, tmp_path)
    payload = set_mod._run_one_verify_attempt(
        project_dir=str(tmp_path / "proj"),
        file_path=None,
        run_after_validate=False,
        input_arguments=None,
        timeout_seconds=10,
        auto_install_packages=False,
        studio_debug_after_run=True,
        attempt_index=1,
        max_attempts=1,
        require_studio_debug=True,
    )
    assert payload["success"] is False
    assert payload["verdict"] == "needs_human"
    assert payload["next_action"] == "start_studio_or_waive"


def test_require_studio_debug_false_allows_pass_when_run_skipped(tmp_path, monkeypatch):
    _stub_validate(monkeypatch, tmp_path)
    payload = set_mod._run_one_verify_attempt(
        project_dir=str(tmp_path / "proj"),
        file_path=None,
        run_after_validate=False,
        input_arguments=None,
        timeout_seconds=10,
        auto_install_packages=False,
        studio_debug_after_run=False,
        attempt_index=1,
        max_attempts=1,
        require_studio_debug=False,
    )
    assert payload["success"] is True
    assert payload["verdict"] == "pass"
    assert payload["next_action"] == "none"
