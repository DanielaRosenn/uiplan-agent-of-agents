"""Tests for skill source path ordering (build_skill_sources)."""

from __future__ import annotations

from pathlib import Path

import pytest

from uipath_claude.skills.sources import SkillOrigin, build_skill_sources


def test_build_skill_sources_order_default_layers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When all default layers exist, origins follow USER > PROJECT > EXTENSIONS > UIPATH_SUBMODULE."""
    fake_home = tmp_path / "home"
    (fake_home / ".cursor" / "skills").mkdir(parents=True)

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    project = tmp_path / "project"
    (project / ".uipath-claude" / "skills").mkdir(parents=True)
    (project / "extensions" / "skills").mkdir(parents=True)
    (project / "skills" / "skills").mkdir(parents=True)

    rows = build_skill_sources(project)
    origins = [o for _, o in rows]

    assert origins == [
        SkillOrigin.USER,
        SkillOrigin.PROJECT,
        SkillOrigin.EXTENSIONS,
        SkillOrigin.UIPATH_SUBMODULE,
    ]


def test_build_skill_sources_config_paths_first(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Custom paths from config.yaml are inserted before defaults and use PROJECT origin."""
    fake_home = tmp_path / "home"
    (fake_home / ".cursor" / "skills").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    project = tmp_path / "project"
    custom = project / "vendor" / "skills"
    custom.mkdir(parents=True)
    (project / ".uipath-claude").mkdir(parents=True)
    cfg = project / ".uipath-claude" / "config.yaml"
    cfg.write_text(
        "skills:\n  sources:\n    - path: vendor/skills\n",
        encoding="utf-8",
    )
    (project / "extensions" / "skills").mkdir(parents=True)
    (project / "skills" / "skills").mkdir(parents=True)

    rows = build_skill_sources(project)
    origins = [o for _, o in rows]
    paths = [Path(p) for p, _ in rows]

    assert origins[0] == SkillOrigin.PROJECT
    assert paths[0] == custom.resolve()
    assert SkillOrigin.USER in origins
    assert SkillOrigin.EXTENSIONS in origins
    assert SkillOrigin.UIPATH_SUBMODULE in origins
