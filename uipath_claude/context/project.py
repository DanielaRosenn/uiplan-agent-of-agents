"""UiPath project context detection."""
import json
from pathlib import Path
from typing import Optional
from uipath_claude.query.state import UiPathProjectContext


def detect_uipath_project(start_path: str) -> Optional[UiPathProjectContext]:
    """
    Detect UiPath project in the given directory or parent directories.
    
    Args:
        start_path: Directory to start searching from
        
    Returns:
        UiPathProjectContext if project found, None otherwise
    """
    current = Path(start_path).resolve()
    
    # Search up to 5 levels up
    for _ in range(5):
        project_json = current / "project.json"
        
        if project_json.exists():
            try:
                data = json.loads(project_json.read_text())
                
                return UiPathProjectContext(
                    project_path=str(current),
                    project_name=data.get("name", current.name),
                    project_type=data.get("projectType", "Unknown"),
                    has_project_json=True,
                    dependencies=list(data.get("dependencies", {}).keys()),
                )
            except Exception:
                pass
        
        # Check for .uiproj file (older format)
        uiproj_files = list(current.glob("*.uiproj"))
        if uiproj_files:
            return UiPathProjectContext(
                project_path=str(current),
                project_name=uiproj_files[0].stem,
                project_type="Unknown",
                has_project_json=False,
            )
        
        if current.parent == current:
            break
        current = current.parent
    
    return None
