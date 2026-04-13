"""Test skills command."""

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.skills import register_skills_command
from uipath_claude.commands.update_skills import register_update_skills_command


def test_skills_command_lists_grouped_sources():
    """Test /skills renders grouped discovered skills."""
    registry = CommandRegistry()
    all_skills = [
        {
            "name": "uipath-platform",
            "path": "C:/repo/skills/skills/uipath-platform/SKILL.md",
            "source_root": "C:/repo/skills/skills",
        },
        {
            "name": "jira-ticket-creation",
            "path": "C:/repo/templates/long-running/.cursor/skills/jira/SKILL.md",
            "source_root": "C:/repo/templates/long-running/.cursor/skills",
        },
    ]

    register_skills_command(
        registry,
        list_skills=lambda: all_skills,
        filter_skills_by_role=lambda _role: all_skills,
    )

    out = registry.execute("skills")
    assert "skills for role" in out.lower()
    assert "uipath-platform" in out
    assert "jira-ticket-creation" in out
    assert "source:" in out.lower()


def test_skills_command_role_filter_empty():
    """Test /skills <role> empty response includes guidance."""
    registry = CommandRegistry()
    register_skills_command(
        registry,
        list_skills=lambda: [{"name": "x", "path": "C:/repo/a/SKILL.md"}],
        filter_skills_by_role=lambda _role: [],
    )
    out = registry.execute("skills", "qa")
    assert "no skills matched that role" in out.lower()


def test_update_skills_info_includes_last_synced(monkeypatch):
    """Test /update-skills --info renders sync metadata."""
    registry = CommandRegistry()
    register_update_skills_command(registry)

    monkeypatch.setattr(
        "uipath_claude.commands.update_skills.get_skills_info",
        lambda: {
            "path": "C:/repo/skills",
            "current_commit": "aaa11111",
            "remote_commit": "bbb22222",
            "last_synced_at": "2026-04-13T12:00:00+00:00",
            "has_updates": True,
            "skills_count": 2,
            "skills": ["foo", "bar"],
        },
    )

    out = registry.execute("update-skills", "--info")
    assert "last synced at:" in out.lower()
    assert "2026-04-13T12:00:00+00:00" in out

