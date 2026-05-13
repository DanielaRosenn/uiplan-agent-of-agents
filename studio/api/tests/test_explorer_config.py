"""Tests for `app.explorer_config`: schema parsing, defaults, error paths."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.explorer_config import (
    DEFAULT_SCAN_GLOBS,
    ExplorerConfigError,
    find_config_path,
    load_config,
    load_config_file,
    render_starter_config,
)


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_load_config_missing_file_returns_defaults_with_detected_type(tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text("{}", encoding="utf-8")
    config = load_config(tmp_path)
    assert config.project.type == "rpa"
    assert config.source_path is None
    # Defaults populate `indexing.scan` for rpa
    assert "rpa" in config.indexing.scan


def test_load_config_full_yaml_round_trips(tmp_path: Path) -> None:
    body = """
project:
  name: Renewal Commitment
  type: mixed
  owner: Sales Operations
overview:
  summary: |
    End-to-end renewal flow.
  stakeholders: [Sales, Finance]
  triggers:
    - { kind: http, description: "POST /commitments" }
  actors:
    - { name: "Sales Rep", role: submitter }
  kpis:
    - { label: volume, value: "120 / day" }
indexing:
  scan:
    ui:    ["src/**/*.tsx"]
    api:   ["backend/**/*.py"]
"""
    _write(tmp_path / ".uiplan" / "explorer.yaml", body)
    config = load_config(tmp_path)
    assert config.project.name == "Renewal Commitment"
    assert config.project.owner == "Sales Operations"
    assert config.overview.summary.startswith("End-to-end")
    assert ("Sales", "Finance") == config.overview.stakeholders
    assert config.overview.triggers[0].kind == "http"
    assert config.overview.kpis[0].value == "120 / day"
    assert config.indexing.scan["ui"] == ("src/**/*.tsx",)


def test_load_config_invalid_yaml_raises(tmp_path: Path) -> None:
    _write(tmp_path / ".uiplan" / "explorer.yaml", "project: [this is not a mapping")
    with pytest.raises(ExplorerConfigError):
        load_config(tmp_path)


def test_load_config_missing_required_keys_raise(tmp_path: Path) -> None:
    _write(tmp_path / ".uiplan" / "explorer.yaml", """
overview:
  triggers:
    - { description: "no kind here" }
""")
    with pytest.raises(ExplorerConfigError, match="kind"):
        load_config(tmp_path)


def test_load_config_top_level_must_be_mapping(tmp_path: Path) -> None:
    _write(tmp_path / ".uiplan" / "explorer.yaml", "- one\n- two\n")
    with pytest.raises(ExplorerConfigError, match="mapping"):
        load_config(tmp_path)


def test_find_config_path_walks_upwards(tmp_path: Path) -> None:
    _write(tmp_path / ".uiplan" / "explorer.yaml", "project: { name: x, type: rpa }")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    found = find_config_path(nested)
    assert found is not None
    assert found.parent.parent == tmp_path


def test_render_starter_config_uses_detected_type(tmp_path: Path) -> None:
    (tmp_path / "langgraph.json").write_text("{}", encoding="utf-8")
    body = render_starter_config(tmp_path)
    assert "type: langgraph" in body
    assert "name: \"" + tmp_path.name + "\"" in body


def test_default_scan_globs_cover_known_project_types() -> None:
    for project_type in ("rpa", "coded-agent", "langgraph", "solution", "mixed", "unknown"):
        assert project_type in DEFAULT_SCAN_GLOBS, project_type
