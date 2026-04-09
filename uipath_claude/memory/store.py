"""Memory storage to global and project-specific locations."""
import os
from pathlib import Path
from typing import Optional


def save_memory(content: str, project_path: Optional[str] = None) -> None:
    """
    Save memory to global or project-specific location.
    
    Args:
        content: Memory content to save
        project_path: Path to UiPath project (if None, saves to global)
    """
    if project_path:
        memory_file = Path(project_path) / ".uipath-claude" / "memory.md"
    else:
        home_dir = Path(os.environ.get("HOME", str(Path.home())))
        memory_file = home_dir / ".uipath-claude" / "memory.md"
    
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    memory_file.write_text(content)
