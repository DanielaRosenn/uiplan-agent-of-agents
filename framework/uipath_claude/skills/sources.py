"""Skill source path resolution with provenance tracking."""

import os
from enum import Enum
from pathlib import Path
from typing import Optional
import yaml


class SkillOrigin(str, Enum):
    """
    Provenance label for a skill directory (not the same as merge order).

    Merge order is defined in ``build_skill_sources`` (config paths first,
    then user, project checkout, extensions, submodule, optional templates).
    When two sources define the same skill name, the earlier path in that
    ordered list wins; its directory is tagged with one of these origins.
    """
    USER = "user"
    PROJECT = "project"
    EXTENSIONS = "extensions"
    UIPATH_SUBMODULE = "uipath-submodule"
    TEMPLATE = "template"


def _load_config(project_root: Path) -> Optional[dict]:
    """Load .uipath-claude/config.yaml if it exists."""
    config_path = project_root / ".uipath-claude" / "config.yaml"
    if config_path.exists():
        try:
            return yaml.safe_load(config_path.read_text())
        except Exception:
            pass
    return None


def build_skill_sources(project_root: Path) -> list[tuple[str, SkillOrigin]]:
    """
    Build ordered skill source directories with provenance.
    
    Returns list of (resolved_path, origin) tuples. Only includes paths that exist.
    Order matters: first source wins when skill names collide.
    
    Priority order (first wins; only existing paths are returned):
      1. Optional paths from `.uipath-claude/config.yaml` `skills.sources` (project origin)
      2. User (`~/.cursor/skills`)
      3. Project (`.uipath-claude/skills`)
      4. Extensions (`extensions/skills`)
      5. UiPath Submodule (`skills/skills`)
      6. Templates (opt-in via `UIPATH_INCLUDE_TEMPLATE_SKILLS`)
    """
    ordered_sources: list[tuple[Path, SkillOrigin]] = []
    
    # Check for config file - custom sources get PROJECT origin
    config = _load_config(project_root)
    if config and "skills" in config and "sources" in config["skills"]:
        for source in config["skills"]["sources"]:
            if "path" in source:
                ordered_sources.append(
                    (project_root / source["path"], SkillOrigin.PROJECT)
                )
    
    # Default sources in priority order
    default_sources: list[tuple[Path, SkillOrigin]] = [
        (Path.home() / ".cursor" / "skills", SkillOrigin.USER),
        (project_root / ".uipath-claude" / "skills", SkillOrigin.PROJECT),
        (project_root / "extensions" / "skills", SkillOrigin.EXTENSIONS),
        (project_root / "skills" / "skills", SkillOrigin.UIPATH_SUBMODULE),
    ]
    
    for source_path, origin in default_sources:
        if not any(p == source_path for p, _ in ordered_sources):
            ordered_sources.append((source_path, origin))

    # Check templates directory (opt-in via env var)
    include_template_skills = os.environ.get(
        "UIPATH_INCLUDE_TEMPLATE_SKILLS", "0"
    ).strip().lower() in {"1", "true", "yes"}
    templates_dir = project_root / "scaffold" / "template"
    if not templates_dir.is_dir():
        templates_dir = project_root / "templates"
    if include_template_skills and templates_dir.exists():
        for path in templates_dir.rglob(".cursor/skills"):
            ordered_sources.append((path, SkillOrigin.TEMPLATE))
        for path in templates_dir.rglob(".claude/skills"):
            ordered_sources.append((path, SkillOrigin.TEMPLATE))

    # Deduplicate and filter to existing paths
    seen: set[str] = set()
    result: list[tuple[str, SkillOrigin]] = []
    for path, origin in ordered_sources:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            result.append((key, origin))
    return result
