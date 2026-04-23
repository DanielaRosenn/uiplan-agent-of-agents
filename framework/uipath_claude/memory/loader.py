"""Memory loading from global and project-specific locations."""
import os
from pathlib import Path
from typing import Optional


def load_memory(project_path: Optional[str] = None) -> str:
    """
    Load memory from global and project-specific locations.
    
    Args:
        project_path: Path to UiPath project (optional)
        
    Returns:
        Combined memory content
    """
    memory_parts = []
    
    # Load global memory
    home_dir = Path(os.environ.get("HOME", str(Path.home())))
    global_memory = home_dir / ".uipath-claude" / "memory.md"
    if global_memory.exists():
        memory_parts.append(global_memory.read_text())
    
    # Load project-specific memory
    if project_path:
        project_memory = Path(project_path) / ".uipath-claude" / "memory.md"
        if project_memory.exists():
            memory_parts.append(project_memory.read_text())
    
    return "\n\n".join(memory_parts)
