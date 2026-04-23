#!/usr/bin/env python
"""Test script to verify UiPath/skills integration."""
import sys
from pathlib import Path

# Add runtime root to path
_REPO = Path(__file__).resolve().parents[2]
_FW = _REPO / "framework"
sys.path.insert(0, str(_FW if (_FW / "uipath_claude").is_dir() else _REPO))


def test_skills_updater():
    """Test the skills updater module."""
    print("=" * 60)
    print("TEST: Skills Updater")
    print("=" * 60)
    
    from uipath_claude.skills.updater import (
        get_skills_info,
        check_for_updates,
    )
    
    info = get_skills_info()
    print(f"  Skills path: {info['path']}")
    print(f"  Exists: {info['exists']}")
    print(f"  Current commit: {info['current_commit']}")
    print(f"  Remote commit: {info['remote_commit']}")
    print(f"  Has updates: {info['has_updates']}")
    print(f"  Skills count: {info['skills_count']}")
    
    if info['skills']:
        print(f"  Skills:")
        for skill in info['skills']:
            print(f"    - {skill}")
    
    has_updates, msg, _, _ = check_for_updates()
    print(f"\n  Update check: {msg}")
    
    return info['exists'] and info['skills_count'] > 0


def test_activity_docs():
    """Test the activity documentation lookup."""
    print("\n" + "=" * 60)
    print("TEST: Activity Documentation")
    print("=" * 60)
    
    from uipath_claude.skills.activity_docs import (
        list_available_packages,
        get_package_versions,
        list_activities,
        get_activity_doc,
        search_activities,
    )
    
    packages = list_available_packages()
    print(f"  Available packages: {len(packages)}")
    for p in packages[:5]:
        print(f"    - {p}")
    if len(packages) > 5:
        print(f"    ... and {len(packages) - 5} more")
    
    # Test Mail package
    mail_versions = get_package_versions("UiPath.Mail.Activities")
    print(f"\n  UiPath.Mail.Activities versions: {mail_versions}")
    
    mail_activities = list_activities("UiPath.Mail.Activities")
    print(f"  Mail activities: {mail_activities}")
    
    # Test doc lookup
    doc = get_activity_doc("UiPath.Mail.Activities", "GetOutlookMailMessages")
    if doc:
        print(f"\n  GetOutlookMailMessages doc found ({len(doc)} chars)")
        print(f"  Preview: {doc[:200]}...")
    else:
        print("  GetOutlookMailMessages doc NOT FOUND")
    
    # Test search
    results = search_activities("outlook")
    print(f"\n  Search 'outlook': {len(results)} results")
    for r in results[:3]:
        print(f"    - {r['package']}: {r['activity']}")
    
    return len(packages) > 0


def test_session_hooks():
    """Test the session hooks module."""
    print("\n" + "=" * 60)
    print("TEST: Session Hooks")
    print("=" * 60)
    
    from uipath_claude.hooks.session_hooks import (
        get_skills_hooks_path,
        load_skills_hooks,
        check_uip_installed,
    )
    
    hooks_path = get_skills_hooks_path()
    print(f"  Hooks path: {hooks_path}")
    print(f"  Hooks path exists: {hooks_path.exists() if hooks_path else False}")
    
    hooks_config = load_skills_hooks()
    print(f"  Hooks config loaded: {bool(hooks_config)}")
    if hooks_config:
        print(f"  Hook events: {list(hooks_config.get('hooks', {}).keys())}")
    
    uip_ok, uip_msg = check_uip_installed()
    print(f"\n  UIP CLI check: {uip_msg}")
    
    return hooks_path is not None


def test_skill_registry():
    """Test the skill registry."""
    print("\n" + "=" * 60)
    print("TEST: Skill Registry")
    print("=" * 60)
    
    from uipath_claude.skills.registry import SkillRegistry, AGENT_SKILLS
    
    print("  Agent skill mappings:")
    for role, skills in AGENT_SKILLS.items():
        print(f"    {role}: {skills}")
    
    registry = SkillRegistry()
    skills = registry.load_skills()
    print(f"\n  Loaded skills: {len(skills)}")
    for skill in skills[:10]:
        print(f"    - {skill['name']} (from {Path(skill.get('source_root', '')).name})")
    if len(skills) > 10:
        print(f"    ... and {len(skills) - 10} more")
    
    # Test filtering
    dev_skills = registry.filter_by_agent("developer")
    print(f"\n  Developer skills: {len(dev_skills)}")
    for s in dev_skills:
        print(f"    - {s['name']}")
    
    return len(skills) > 0


def test_update_skills_command():
    """Test the /update-skills command."""
    print("\n" + "=" * 60)
    print("TEST: /update-skills Command")
    print("=" * 60)
    
    from uipath_claude.commands.update_skills import register_update_skills_command
    from uipath_claude.commands.registry import CommandRegistry
    
    registry = CommandRegistry()
    register_update_skills_command(registry)
    
    # Test --info
    result = registry.execute("update-skills", "--info")
    print("  /update-skills --info:")
    for line in result.split("\n")[:10]:
        print(f"    {line}")
    
    # Test --check
    result = registry.execute("update-skills", "--check")
    print(f"\n  /update-skills --check:")
    print(f"    {result}")
    
    return "update-skills" in registry.commands


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("UiPath/skills Integration Tests")
    print("=" * 60 + "\n")
    
    results = {}
    
    try:
        results["Skills Updater"] = test_skills_updater()
    except Exception as e:
        print(f"  ERROR: {e}")
        results["Skills Updater"] = False
    
    try:
        results["Activity Docs"] = test_activity_docs()
    except Exception as e:
        print(f"  ERROR: {e}")
        results["Activity Docs"] = False
    
    try:
        results["Session Hooks"] = test_session_hooks()
    except Exception as e:
        print(f"  ERROR: {e}")
        results["Session Hooks"] = False
    
    try:
        results["Skill Registry"] = test_skill_registry()
    except Exception as e:
        print(f"  ERROR: {e}")
        results["Skill Registry"] = False
    
    try:
        results["Update Command"] = test_update_skills_command()
    except Exception as e:
        print(f"  ERROR: {e}")
        results["Update Command"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_test in results.items():
        status = "PASSED" if passed_test else "FAILED"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
