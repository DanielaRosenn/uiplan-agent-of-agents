# tests/unit/test_memory_loader.py
import pytest
from pathlib import Path

from agent.memory.loader import load_memory, MemoryContent, get_default_global_dir


class TestMemoryLoader:
    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Create temp directories for global and project memory."""
        global_dir = tmp_path / "global"
        project_dir = tmp_path / "project"
        global_dir.mkdir()
        project_dir.mkdir()
        return global_dir, project_dir
    
    def test_loads_global_memory(self, temp_dirs):
        """Loads memory from global directory."""
        global_dir, project_dir = temp_dirs
        
        memory_file = global_dir / "memory.md"
        memory_file.write_text("# Global Memory\nRemember this.")
        
        result = load_memory(global_dir=global_dir, project_dir=project_dir)
        
        assert "Global Memory" in result.content
        assert "Remember this" in result.content
    
    def test_loads_project_memory(self, temp_dirs):
        """Loads memory from project directory."""
        global_dir, project_dir = temp_dirs
        
        uipath_dir = project_dir / ".uipath-claude"
        uipath_dir.mkdir()
        memory_file = uipath_dir / "memory.md"
        memory_file.write_text("# Project Memory\nProject-specific info.")
        
        result = load_memory(global_dir=global_dir, project_dir=project_dir)
        
        assert "Project Memory" in result.content
    
    def test_combines_global_and_project_memory(self, temp_dirs):
        """Combines both global and project memory."""
        global_dir, project_dir = temp_dirs
        
        global_memory = global_dir / "memory.md"
        global_memory.write_text("# Global\nGlobal info.")
        
        uipath_dir = project_dir / ".uipath-claude"
        uipath_dir.mkdir()
        project_memory = uipath_dir / "memory.md"
        project_memory.write_text("# Project\nProject info.")
        
        result = load_memory(global_dir=global_dir, project_dir=project_dir)
        
        assert "Global info" in result.content
        assert "Project info" in result.content
    
    def test_returns_empty_when_no_memory(self, temp_dirs):
        """Returns empty content when no memory files exist."""
        global_dir, project_dir = temp_dirs
        
        result = load_memory(global_dir=global_dir, project_dir=project_dir)
        
        assert result.content == ""
