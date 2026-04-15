"""Test skill source path resolution."""

from pathlib import Path

from uipath_claude.skills.sources import build_skill_sources, SkillOrigin


def test_build_skill_sources_precedence(tmp_path, monkeypatch):
    """Test source order matches required precedence."""
    project_local = tmp_path / ".uipath-claude" / "skills"
    user_local = tmp_path / "home" / ".cursor" / "skills"
    extensions = tmp_path / "extensions" / "skills"
    official = tmp_path / "skills" / "skills"
    cato = tmp_path / "templates" / "long-running" / ".cursor" / "skills"

    project_local.mkdir(parents=True)
    user_local.mkdir(parents=True)
    extensions.mkdir(parents=True)
    official.mkdir(parents=True)
    cato.mkdir(parents=True)

    monkeypatch.setattr("uipath_claude.skills.sources.Path.home", lambda: tmp_path / "home")

    sources = build_skill_sources(tmp_path)
    
    # Extract just paths for comparison
    paths = [p for p, _ in sources]
    
    # User comes first (highest priority)
    assert paths[0] == str(user_local.resolve())
    
    # Check all expected paths are present
    assert str(project_local.resolve()) in paths
    assert str(extensions.resolve()) in paths
    assert str(official.resolve()) in paths
    
    # Templates not included by default
    assert str(cato.resolve()) not in paths


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
    
    # Extract just paths for comparison
    paths = [p for p, _ in sources]
    
    assert str(cato.resolve()) in paths
    
    # Also verify the origin is correct
    cato_source = next((p, o) for p, o in sources if str(cato.resolve()) == p)
    assert cato_source[1] == SkillOrigin.TEMPLATE


def test_build_skill_sources_skips_missing_paths(tmp_path, monkeypatch):
    """Test non-existing source paths are ignored."""
    monkeypatch.setattr("uipath_claude.skills.sources.Path.home", lambda: tmp_path / "home")
    sources = build_skill_sources(tmp_path)
    assert sources == []
