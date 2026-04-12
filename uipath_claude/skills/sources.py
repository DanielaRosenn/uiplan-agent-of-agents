"""Skill source path resolution."""

from pathlib import Path


def build_skill_sources(project_root: Path) -> list[str]:
    """Build ordered skill source directories."""
    ordered_sources: list[Path] = [
        project_root / ".uipath-claude" / "skills",
        Path.home() / ".cursor" / "skills",
        project_root / "skills" / "skills",
    ]

    templates_dir = project_root / "templates"
    if templates_dir.exists():
        for path in templates_dir.rglob(".cursor/skills"):
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

