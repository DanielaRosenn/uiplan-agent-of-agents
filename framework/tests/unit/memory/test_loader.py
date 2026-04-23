"""Test memory loading."""
from pathlib import Path
from uipath_claude.memory.loader import load_memory


def test_load_memory_global_only(tmp_path, monkeypatch):
    """Test loading global memory only."""
    # Create global memory
    global_memory = tmp_path / ".uipath-claude" / "memory.md"
    global_memory.parent.mkdir(parents=True)
    global_memory.write_text("# Global Memory\n\nGlobal context here.")
    
    monkeypatch.setenv("HOME", str(tmp_path))
    
    memory = load_memory(project_path=None)
    
    assert "Global Memory" in memory
    assert "Global context here" in memory


def test_load_memory_with_project(tmp_path, monkeypatch):
    """Test loading global + project memory."""
    # Create global memory
    global_memory = tmp_path / ".uipath-claude" / "memory.md"
    global_memory.parent.mkdir(parents=True)
    global_memory.write_text("# Global Memory\n\nGlobal context.")
    
    # Create project memory
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_memory = project_dir / ".uipath-claude" / "memory.md"
    project_memory.parent.mkdir(parents=True)
    project_memory.write_text("# Project Memory\n\nProject context.")
    
    monkeypatch.setenv("HOME", str(tmp_path))
    
    memory = load_memory(project_path=str(project_dir))
    
    assert "Global Memory" in memory
    assert "Project Memory" in memory
    assert memory.index("Global Memory") < memory.index("Project Memory")


def test_load_memory_no_files(tmp_path, monkeypatch):
    """Test loading memory when no files exist."""
    monkeypatch.setenv("HOME", str(tmp_path))
    memory = load_memory(project_path=None)
    assert memory == ""
