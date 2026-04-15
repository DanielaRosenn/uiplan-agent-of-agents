"""Tests for skill source path resolution with provenance."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from uipath_claude.skills.sources import (
    SkillOrigin,
    build_skill_sources,
)


class TestSkillOrigin:
    """Tests for SkillOrigin enum."""
    
    def test_origin_enum_values(self):
        """Verify SkillOrigin enum has all expected values."""
        assert SkillOrigin.USER.value == "user"
        assert SkillOrigin.PROJECT.value == "project"
        assert SkillOrigin.EXTENSIONS.value == "extensions"
        assert SkillOrigin.UIPATH_SUBMODULE.value == "uipath-submodule"
        assert SkillOrigin.TEMPLATE.value == "template"
    
    def test_origin_enum_is_str(self):
        """Verify SkillOrigin values can be used as strings."""
        # SkillOrigin inherits from str, so .value gives the string
        assert SkillOrigin.USER.value == "user"
        assert SkillOrigin.EXTENSIONS.value == "extensions"
        # Can compare directly to strings
        assert SkillOrigin.USER == "user"
        assert SkillOrigin.EXTENSIONS == "extensions"
    
    def test_origin_enum_all_values(self):
        """Verify all expected origins exist."""
        all_origins = list(SkillOrigin)
        assert len(all_origins) == 5


class TestBuildSkillSources:
    """Tests for build_skill_sources function."""
    
    def test_sources_return_origin_tuples(self, tmp_path):
        """Verify build_skill_sources returns (path, origin) tuples."""
        # Create a valid skill directory
        skills_dir = tmp_path / "skills" / "skills"
        skills_dir.mkdir(parents=True)
        
        sources = build_skill_sources(tmp_path)
        
        # Should return list of tuples
        assert isinstance(sources, list)
        for item in sources:
            assert isinstance(item, tuple)
            assert len(item) == 2
            path, origin = item
            assert isinstance(path, str)
            assert isinstance(origin, SkillOrigin)
    
    def test_source_order_priority(self, tmp_path):
        """Verify user > project > extensions > submodule order."""
        # Create all directories so they appear in results
        (tmp_path / ".uipath-claude" / "skills").mkdir(parents=True)
        (tmp_path / "extensions" / "skills").mkdir(parents=True)
        (tmp_path / "skills" / "skills").mkdir(parents=True)
        
        # Mock home directory to be inside tmp_path
        mock_home = tmp_path / "home"
        mock_user_skills = mock_home / ".cursor" / "skills"
        mock_user_skills.mkdir(parents=True)
        
        with patch.object(Path, "home", return_value=mock_home):
            sources = build_skill_sources(tmp_path)
        
        # Extract origins in order
        origins = [origin for _, origin in sources]
        
        # Find indices of each origin (first occurrence)
        user_idx = next((i for i, o in enumerate(origins) if o == SkillOrigin.USER), -1)
        project_idx = next((i for i, o in enumerate(origins) if o == SkillOrigin.PROJECT), -1)
        ext_idx = next((i for i, o in enumerate(origins) if o == SkillOrigin.EXTENSIONS), -1)
        submod_idx = next((i for i, o in enumerate(origins) if o == SkillOrigin.UIPATH_SUBMODULE), -1)
        
        # Verify order (user should come before project, etc.)
        assert user_idx < project_idx, "User should come before project"
        assert ext_idx < submod_idx, "Extensions should come before submodule"
    
    def test_nonexistent_dirs_excluded(self, tmp_path):
        """Verify missing directories are filtered out."""
        # Don't create any skill directories
        sources = build_skill_sources(tmp_path)
        
        # All returned paths should exist
        for path, _ in sources:
            assert Path(path).exists(), f"Path should exist: {path}"
    
    def test_template_sources_opt_in(self, tmp_path):
        """Verify templates only included when env var set."""
        # Create template skills directory
        template_skills = tmp_path / "templates" / "my-template" / ".cursor" / "skills"
        template_skills.mkdir(parents=True)
        
        # Without env var, templates should not be included
        with patch.dict(os.environ, {"UIPATH_INCLUDE_TEMPLATE_SKILLS": "0"}, clear=False):
            sources = build_skill_sources(tmp_path)
            origins = [origin for _, origin in sources]
            assert SkillOrigin.TEMPLATE not in origins
        
        # With env var, templates should be included
        with patch.dict(os.environ, {"UIPATH_INCLUDE_TEMPLATE_SKILLS": "1"}, clear=False):
            sources = build_skill_sources(tmp_path)
            origins = [origin for _, origin in sources]
            assert SkillOrigin.TEMPLATE in origins
    
    def test_deduplication(self, tmp_path):
        """Verify duplicate paths are deduplicated."""
        # Create a single directory that could be listed multiple times
        skills_dir = tmp_path / "skills" / "skills"
        skills_dir.mkdir(parents=True)
        
        sources = build_skill_sources(tmp_path)
        
        # Check no duplicate paths
        paths = [path for path, _ in sources]
        assert len(paths) == len(set(paths)), "Should not have duplicate paths"
    
    def test_extensions_origin_assigned(self, tmp_path):
        """Verify extensions directory gets EXTENSIONS origin."""
        ext_dir = tmp_path / "extensions" / "skills"
        ext_dir.mkdir(parents=True)
        
        sources = build_skill_sources(tmp_path)
        
        # Find extensions source
        ext_sources = [(p, o) for p, o in sources if o == SkillOrigin.EXTENSIONS]
        assert len(ext_sources) == 1
        assert "extensions" in ext_sources[0][0]
    
    def test_uipath_submodule_origin_assigned(self, tmp_path):
        """Verify skills/skills directory gets UIPATH_SUBMODULE origin."""
        submod_dir = tmp_path / "skills" / "skills"
        submod_dir.mkdir(parents=True)
        
        sources = build_skill_sources(tmp_path)
        
        # Find submodule source
        submod_sources = [(p, o) for p, o in sources if o == SkillOrigin.UIPATH_SUBMODULE]
        assert len(submod_sources) == 1
        assert "skills" in submod_sources[0][0]
