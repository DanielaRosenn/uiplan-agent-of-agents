"""Test skill source path resolution."""

from pathlib import Path

from uipath_claude.skills.sources import build_skill_sources


def test_build_skill_sources_precedence(tmp_path, monkeypatch):
    """Test source order matches required precedence."""
    project_local = tmp_path / ".uipath-claude" / "skills"
    user_local = tmp_path / "home" / ".cursor" / "skills"
    official = tmp_path / "skills" / "skills"
    cato = tmp_path / "templates" / "long-running" / ".cursor" / "skills"

    project_local.mkdir(parents=True)
    user_local.mkdir(parents=True)
    official.mkdir(parents=True)
    cato.mkdir(parents=True)

    monkeypatch.setattr("uipath_claude.skills.sources.Path.home", lambda: tmp_path / "home")

    sources = build_skill_sources(tmp_path)
    assert sources[0] == str(project_local.resolve())
    assert sources[1] == str(user_local.resolve())
    assert sources[2] == str(official.resolve())
    assert str(cato.resolve()) not in sources


def test_build_skill_sources_can_include_template_skills(tmp_path, monkeypatch):
    project_local = tmp_path / ".uipath-claude" / "skills"
    user_local = tmp_path / "home" / ".cursor" / "skills"
    official = tmp_path / "skills" / "skills"
    cato = tmp_path / "templates" / "long-running" / ".cursor" / "skills"

    project_local.mkdir(parents=True)
    user_local.mkdir(parents=True)
    official.mkdir(parents=True)
    cato.mkdir(parents=True)

    monkeypatch.setattr("uipath_claude.skills.sources.Path.home", lambda: tmp_path / "home")
    monkeypatch.setenv("UIPATH_INCLUDE_TEMPLATE_SKILLS", "1")

    sources = build_skill_sources(tmp_path)
    assert str(cato.resolve()) in sources


def test_build_skill_sources_skips_missing_paths(tmp_path, monkeypatch):
    """Test non-existing source paths are ignored."""
    monkeypatch.setattr("uipath_claude.skills.sources.Path.home", lambda: tmp_path / "home")
    sources = build_skill_sources(tmp_path)
    assert sources == []

