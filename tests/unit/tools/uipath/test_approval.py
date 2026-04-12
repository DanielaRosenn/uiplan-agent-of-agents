"""Tests for UiPath CLI approval guard."""
from uipath_claude.tools.uipath.approval import check_cli_approval


def test_check_cli_approval_allows_when_not_required():
    allowed, message = check_cli_approval(env={})
    assert allowed is True
    assert message == ""


def test_check_cli_approval_blocks_when_required_without_approval():
    allowed, message = check_cli_approval(
        env={"UIPATH_CLAUDE_REQUIRE_APPROVAL": "true"}
    )
    assert allowed is False
    assert "approval required" in message.lower()
    assert "UIPATH_CLAUDE_CLI_APPROVED" in message
    assert "UIPATH_CLAUDE_APPROVED" in message


def test_check_cli_approval_allows_when_explicitly_approved():
    allowed, message = check_cli_approval(
        env={
            "UIPATH_CLAUDE_REQUIRE_APPROVAL": "true",
            "UIPATH_CLAUDE_CLI_APPROVED": "true",
        }
    )
    assert allowed is True
    assert message == ""


def test_check_cli_approval_allows_when_legacy_alias_is_approved():
    allowed, message = check_cli_approval(
        env={
            "UIPATH_CLAUDE_REQUIRE_APPROVAL": "true",
            "UIPATH_CLAUDE_APPROVED": "true",
        }
    )
    assert allowed is True
    assert message == ""
