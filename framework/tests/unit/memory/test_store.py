"""Test memory storage."""
from pathlib import Path
from uipath_claude.memory.store import save_memory


def test_save_memory_global(tmp_path, monkeypatch):
    """Test saving global memory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    
    save_memory("# Test Memory\n\nTest content.", project_path=None)
    
    global_memory = tmp_path / ".uipath-claude" / "memory.md"
    assert global_memory.exists()
    assert global_memory.read_text() == "# Test Memory\n\nTest content."


def test_save_memory_project(tmp_path):
    """Test saving project memory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    save_memory("# Project Memory\n\nProject content.", project_path=str(project_dir))
    
    project_memory = project_dir / ".uipath-claude" / "memory.md"
    assert project_memory.exists()
    assert project_memory.read_text() == "# Project Memory\n\nProject content."
