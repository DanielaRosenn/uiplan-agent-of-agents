"""Load memory content from global and project directories."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MemoryContent:
    """Loaded memory content."""
    
    content: str
    global_path: Optional[Path] = None
    project_path: Optional[Path] = None


def get_default_global_dir() -> Path:
    """Get the default global memory directory."""
    return Path.home() / ".uipath-claude"


def load_memory(
    global_dir: Optional[Path] = None,
    project_dir: Optional[Path] = None,
) -> MemoryContent:
    """
    Load memory from global and project directories.
    
    Memory files are named 'memory.md' and contain markdown content
    that will be injected into the agent's system prompt.
    
    Args:
        global_dir: Global config directory (default: ~/.uipath-claude)
        project_dir: Project directory to search for .uipath-claude/memory.md
        
    Returns:
        MemoryContent with combined content
    """
    parts = []
    global_path = None
    project_path = None
    
    # Load global memory
    if global_dir is None:
        global_dir = get_default_global_dir()
    
    global_memory = global_dir / "memory.md"
    if global_memory.exists():
        try:
            content = global_memory.read_text(encoding="utf-8")
            if content.strip():
                parts.append(f"## Global Memory\n\n{content}")
                global_path = global_memory
        except IOError:
            pass
    
    # Load project memory
    if project_dir:
        project_memory = project_dir / ".uipath-claude" / "memory.md"
        if project_memory.exists():
            try:
                content = project_memory.read_text(encoding="utf-8")
                if content.strip():
                    parts.append(f"## Project Memory\n\n{content}")
                    project_path = project_memory
            except IOError:
                pass
    
    return MemoryContent(
        content="\n\n".join(parts),
        global_path=global_path,
        project_path=project_path,
    )
