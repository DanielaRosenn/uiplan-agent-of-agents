"""Regression checks to prevent placeholder output regressions."""

from pathlib import Path


def test_no_placeholder_strings_in_runtime_commands():
    """Ensure runtime command/tool files do not ship placeholder strings."""
    blocked_strings = [
        "to be implemented",
        "TODO: Implement",
    ]
    target_files = [
        Path("uipath_claude/commands/skills.py"),
        Path("uipath_claude/commands/bootstrap.py"),
        Path("uipath_claude/commands/status.py"),
        Path("uipath_claude/commands/analyze.py"),
        Path("uipath_claude/commands/validate.py"),
        Path("uipath_claude/tools/uipath/askai.py"),
        Path("uipath_claude/tools/uipath/orchestrator.py"),
        Path("uipath_claude/tools/uipath/integration_service.py"),
        Path("uipath_claude/query/bootstrap.py"),
    ]

    failures = []
    for file_path in target_files:
        content = file_path.read_text(encoding="utf-8")
        for token in blocked_strings:
            if token in content:
                failures.append(f"{file_path}: contains '{token}'")

    assert not failures, "\n".join(failures)

