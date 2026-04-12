"""Skill source path resolution."""

from pathlib import Path
from typing import Optional
import yaml


def _load_config(project_root: Path) -> Optional[dict]:
    """Load .uipath-claude/config.yaml if it exists."""
    config_path = project_root / ".uipath-claude" / "config.yaml"
    if config_path.exists():
        try:
            return yaml.safe_load(config_path.read_text())
        except Exception:
            pass
    return None


def build_skill_sources(project_root: Path) -> list[str]:
    """Build ordered skill source directories.
    
    If .uipath-claude/config.yaml exists, uses skill sources from config.
    Otherwise falls back to default paths.
    """
    ordered_sources: list[Path] = []
    
    # Check for config file
    config = _load_config(project_root)
    if config and "skills" in config and "sources" in config["skills"]:
        # Use configured skill sources
        for source in config["skills"]["sources"]:
            if "path" in source:
                ordered_sources.append(project_root / source["path"])
    
    # Add default sources
    default_sources = [
        project_root / ".uipath-claude" / "skills",
        project_root / ".claude" / "skills" / "base",
        project_root / ".claude" / "skills",
        Path.home() / ".cursor" / "skills",
        project_root / "skills" / "skills",
    ]
    
    for source in default_sources:
        if source not in ordered_sources:
            ordered_sources.append(source)

    # Check templates directory
    templates_dir = project_root / "templates"
    if templates_dir.exists():
        for path in templates_dir.rglob(".cursor/skills"):
            ordered_sources.append(path)
        for path in templates_dir.rglob(".claude/skills"):
            ordered_sources.append(path)

    seen: set[str] = set()
    result: list[str] = []
    for path in ordered_sources:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            result.append(key)
    return result

