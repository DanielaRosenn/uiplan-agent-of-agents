"""Tests for harvesting upstream SKILL.md files into library proposals."""
from __future__ import annotations

from pathlib import Path

import pytest

from uipath_claude.library import harvest
from uipath_claude.library.proposals import PROPOSALS_ENV_VAR, ProposalStore


def _write_skill(root: Path, skill_id: str, name: str, desc: str, body: str) -> None:
    d = root / "skills" / skill_id
    d.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: \"{desc}\"\n---\n\n{body}"
    (d / "SKILL.md").write_text(content, encoding="utf-8")


@pytest.fixture
def fake_upstream(tmp_path, monkeypatch):
    root = tmp_path / "skills"
    root.mkdir()
    _write_skill(root, "uipath-rpa", "uipath-rpa", "RPA assistant", "# Body A\n")
    _write_skill(root, "uipath-agents", "uipath-agents", "Agents toolkit", "# Body B\n")
    monkeypatch.setattr(harvest, "get_skills_submodule_path", lambda: root)
    # Redirect proposals store to temp.
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path / "props"))
    return root


def test_harvest_proposes_new_sections(fake_upstream):
    result = harvest.harvest_upstream_skills()
    assert sorted(result.proposed) == ["uipath-agents", "uipath-rpa"]
    store = ProposalStore()
    pending = store.list_pending()
    titles = sorted(p.section_title for p in pending)
    assert titles == ["uipath-agents", "uipath-rpa"]
    assert all("Harvested from UiPath/skills" in p.content for p in pending)


def test_harvest_idempotent(fake_upstream):
    harvest.harvest_upstream_skills()
    result2 = harvest.harvest_upstream_skills()
    assert result2.proposed == []
    assert len(result2.skipped_existing) == 2


def test_harvest_skips_empty_body(fake_upstream):
    # Overwrite with only frontmatter
    (fake_upstream / "skills" / "uipath-rpa" / "SKILL.md").write_text(
        "---\nname: uipath-rpa\ndescription: x\n---\n", encoding="utf-8"
    )
    result = harvest.harvest_upstream_skills()
    assert "uipath-rpa" in result.skipped_missing
    assert "uipath-agents" in result.proposed
