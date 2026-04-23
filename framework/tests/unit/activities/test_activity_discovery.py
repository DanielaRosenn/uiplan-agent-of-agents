"""Tests for ActivityDiscovery."""

from pathlib import Path
from unittest.mock import patch

from uipath_claude.activities.discovery import ActivityDiscovery


def test_find_activity_in_local_docs(tmp_path: Path) -> None:
    local_docs = tmp_path / ".local" / "docs" / "packages" / "UiPath.Mail.Activities"
    local_docs.mkdir(parents=True)
    (local_docs / "GetOutlookMailMessages.md").write_text(
        "# GetOutlookMailMessages\nReads emails", encoding="utf-8"
    )
    disc = ActivityDiscovery(skills_root=tmp_path)
    result = disc.find_activity("GetOutlookMailMessages", tmp_path)
    assert result is not None
    assert result.source == "local_docs"


def test_find_activity_fallback_to_bundled(tmp_path: Path) -> None:
    bundled = tmp_path / "skills" / "uipath-rpa" / "references" / "activity-docs"
    pkg = bundled / "UiPath.Excel.Activities"
    pkg.mkdir(parents=True)
    (pkg / "ReadRange.md").write_text("# ReadRange\nReads range", encoding="utf-8")
    disc = ActivityDiscovery(skills_root=tmp_path)
    result = disc.find_activity("ReadRange", tmp_path)
    assert result is not None
    assert result.source == "bundled"


def test_find_activity_cache(tmp_path: Path) -> None:
    disc = ActivityDiscovery(skills_root=tmp_path)
    with patch.object(disc, "_search_live", return_value=None):
        assert disc.find_activity("UnknownThing", tmp_path) is None
        assert disc.find_activity("UnknownThing", tmp_path) is None
