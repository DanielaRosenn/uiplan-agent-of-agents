"""Regression checks to prevent placeholder output regressions."""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNTIME = _REPO_ROOT / "framework" / "uipath_claude"


def test_no_placeholder_strings_in_runtime_commands():
    """Ensure runtime command/tool files do not ship placeholder strings."""
    blocked_strings = [
        "to be implemented",
        "TODO: Implement",
    ]
    target_files = [
        _RUNTIME / "commands/skills.py",
        _RUNTIME / "commands/bootstrap.py",
        _RUNTIME / "commands/status.py",
        _RUNTIME / "commands/analyze.py",
        _RUNTIME / "commands/validate.py",
        _RUNTIME / "tools/uipath/askai.py",
        _RUNTIME / "tools/uipath/orchestrator.py",
        _RUNTIME / "tools/uipath/integration_service.py",
        _RUNTIME / "query/bootstrap.py",
    ]

    failures = []
    for file_path in target_files:
        content = file_path.read_text(encoding="utf-8")
        for token in blocked_strings:
            if token in content:
                failures.append(f"{file_path}: contains '{token}'")

    assert not failures, "\n".join(failures)

