"""Regression: skill prompts must not suggest XML-style tool invocations (Bedrock uses JSON)."""

from __future__ import annotations

from pathlib import Path

_FORBIDDEN = (
    "<parameter name=",
    "<invoke name=",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_skill_markdown_has_no_xml_tool_antipatterns() -> None:
    skills_root = _repo_root() / "skills" / "skills"
    if not skills_root.is_dir():
        return
    offenders: list[str] = []
    for path in skills_root.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pat in _FORBIDDEN:
            if pat in text:
                offenders.append(f"{path.relative_to(_repo_root())}: contains {pat!r}")
    assert not offenders, "\n".join(offenders[:25])
