"""Hook configuration loading."""
import json
from pathlib import Path
from typing import Dict, List


def load_hooks_config(project_path: str) -> Dict[str, List[str]]:
    """
    Load hooks configuration from project directory.
    
    Args:
        project_path: Path to project directory
        
    Returns:
        Dictionary mapping event names to shell commands
    """
    hooks_file = Path(project_path) / ".uipath-claude" / "hooks.json"
    
    if not hooks_file.exists():
        return {}
    
    try:
        return json.loads(hooks_file.read_text())
    except Exception:
        return {}
