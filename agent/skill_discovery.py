"""Dynamic skill discovery system for UiPath skills repository."""

from dataclasses import dataclass
from pathlib import Path
from typing import List
import yaml
import re


@dataclass
class SkillMetadata:
    """
    Metadata for a UiPath skill parsed from SKILL.md.

    Attributes:
        name: Skill name (from frontmatter or directory name)
        description: Full description from frontmatter
        trigger_patterns: Extracted trigger phrases
        references: List of reference doc paths
        assets: List of asset file paths
        full_prompt: Complete SKILL.md content (used as system prompt)
        skill_dir: Path to skill directory
    """
    name: str
    description: str
    trigger_patterns: List[str]
    references: List[Path]
    assets: List[Path]
    full_prompt: str
    skill_dir: Path


class SkillDiscovery:
    """
    Scans UiPath skills repository and builds dynamic registry.

    Usage:
        discovery = SkillDiscovery(Path("skills"))
        registry = discovery.discover_all_skills()
        skill = registry["uipath-rpa-workflows"]
    """

    def __init__(self, skills_repo_path: Path):
        """
        Initialize skill discovery.

        Args:
            skills_repo_path: Path to cloned UiPath skills repository
        """
        self.skills_path = skills_repo_path / "skills" if (skills_repo_path / "skills").exists() else skills_repo_path
        self.registry = {}

    def discover_all_skills(self) -> dict[str, SkillMetadata]:
        """
        Walk skills directory and parse all SKILL.md files.

        Returns:
            Dictionary mapping skill name to SkillMetadata
        """
        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md_path = skill_dir / "SKILL.md"
            if not skill_md_path.exists():
                continue

            skill_meta = self._parse_skill_metadata(skill_dir)
            if skill_meta is not None:
                self.registry[skill_meta.name] = skill_meta

        return self.registry

    def _parse_skill_metadata(self, skill_dir: Path) -> SkillMetadata | None:
        """
        Parse SKILL.md YAML frontmatter and content.

        Args:
            skill_dir: Path to skill directory

        Returns:
            SkillMetadata with parsed information, or None if parsing fails
        """
        # Read SKILL.md with error handling
        try:
            skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            # Skip skills with unreadable SKILL.md files
            print(f"Warning: Skipping skill {skill_dir.name} - {type(e).__name__}: {e}")
            return None

        # Parse YAML frontmatter
        meta = {}
        body = skill_md

        if skill_md.startswith("---"):
            parts = skill_md.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2]
                # Parse YAML with error handling
                try:
                    meta = yaml.safe_load(frontmatter) or {}
                except yaml.YAMLError as e:
                    # Skip skills with malformed YAML
                    print(f"Warning: Skipping skill {skill_dir.name} - YAML error: {e}")
                    return None

        # Extract trigger patterns
        description = meta.get("description", "")
        triggers = self._extract_triggers(description)

        # Scan references and assets
        references = self._scan_references(skill_dir)
        assets = self._scan_assets(skill_dir)

        return SkillMetadata(
            name=meta.get("name", skill_dir.name),
            description=description,
            trigger_patterns=triggers,
            references=references,
            assets=assets,
            full_prompt=skill_md,
            skill_dir=skill_dir,
        )

    def _extract_triggers(self, description: str) -> List[str]:
        """
        Extract trigger patterns from description.

        Looks for "TRIGGER when:" section and parses comma-separated phrases.

        Args:
            description: Skill description text

        Returns:
            List of trigger phrases
        """
        triggers = []

        if "TRIGGER when:" in description:
            trigger_section = description.split("TRIGGER when:")[1]
            trigger_section = trigger_section.split("DO NOT TRIGGER")[0]

            # Split on commas or newlines
            phrases = re.split(r'[,\n]', trigger_section)
            triggers = [p.strip() for p in phrases if p.strip()]

        return triggers

    def _scan_references(self, skill_dir: Path) -> List[Path]:
        """Find all reference docs in skill/references/."""
        ref_dir = skill_dir / "references"
        if ref_dir.exists() and ref_dir.is_dir():
            return list(ref_dir.glob("*.md"))
        return []

    def _scan_assets(self, skill_dir: Path) -> List[Path]:
        """Find all assets in skill/assets/."""
        asset_dir = skill_dir / "assets"
        if asset_dir.exists() and asset_dir.is_dir():
            return list(asset_dir.iterdir())
        return []
