"""Approval middleware: deny, allow-once, allow-always."""
from __future__ import annotations

from uipath_claude.tools.approval import ApprovalDecision, ApprovalPolicy, is_destructive


def test_is_destructive_set() -> None:
    assert is_destructive("write_file") is True
    assert is_destructive("read_project_json") is False


def test_policy_allow_always_remembers() -> None:
    p = ApprovalPolicy(prompter=lambda name, args: ApprovalDecision.ALLOW_ALWAYS)
    assert p.check("write_file", {"file_path": "x"}) is True
    p2 = ApprovalPolicy(prompter=lambda name, args: ApprovalDecision.DENY, preapproved={"write_file"})
    assert p2.check("write_file", {"file_path": "y"}) is True


def test_policy_deny_blocks() -> None:
    p = ApprovalPolicy(prompter=lambda name, args: ApprovalDecision.DENY)
    assert p.check("deploy_to_orchestrator", {"url": "x"}) is False


def test_non_destructive_auto_allow() -> None:
    p = ApprovalPolicy(prompter=lambda name, args: ApprovalDecision.DENY)
    assert p.check("list_directory", {"directory_path": "."}) is True


def test_allow_once() -> None:
    p = ApprovalPolicy(prompter=lambda name, args: ApprovalDecision.ALLOW_ONCE)
    assert p.check("write_file", {}) is True
    assert p.check("write_file", {}) is False
