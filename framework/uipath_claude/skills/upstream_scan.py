"""Detect new/changed skills and tools in the UiPath/skills submodule.

Used by the CLI (``/scan-upstream-skills``), by session hooks (to surface a
short banner), and by tests. Emits a structured diff so the agent can decide
whether to propose library updates without mutating the submodule.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from uipath_claude.skills.updater import (
    get_skills_submodule_path,
    run_git_command,
)

STATE_FILENAME = ".upstream_skills_state.json"


@dataclass
class SkillsSnapshot:
    commit: str = ""
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)  # top-level uip-like tool dirs

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillsSnapshot":
        return cls(
            commit=data.get("commit", ""),
            skills=list(data.get("skills", [])),
            tools=list(data.get("tools", [])),
        )


def _state_path() -> Path:
    skills_path = get_skills_submodule_path()
    return skills_path.parent / STATE_FILENAME


def _list_skill_ids(skills_root: Path) -> list[str]:
    skills_dir = skills_root / "skills"
    if not skills_dir.exists():
        return []
    return sorted(
        d.name
        for d in skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


def _list_tool_dirs(skills_root: Path) -> list[str]:
    """Top-level non-skill directories that look like shippable tool packs."""
    candidates = ("agents", "hooks", "scripts", ".claude", ".claude-plugin")
    return sorted(
        name for name in candidates if (skills_root / name).exists()
    )


def _current_commit(skills_root: Path) -> str:
    ok, out = run_git_command(["rev-parse", "HEAD"], skills_root)
    return (out[:40] if ok else "").strip()


def take_snapshot(skills_root: Path | None = None) -> SkillsSnapshot:
    root = skills_root or get_skills_submodule_path()
    return SkillsSnapshot(
        commit=_current_commit(root),
        skills=_list_skill_ids(root),
        tools=_list_tool_dirs(root),
    )


def load_prev_snapshot(path: Path | None = None) -> SkillsSnapshot | None:
    p = path or _state_path()
    if not p.exists():
        return None
    try:
        return SkillsSnapshot.from_dict(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return None


def save_snapshot(snap: SkillsSnapshot, path: Path | None = None) -> None:
    """Atomically persist a snapshot (tmp file + ``os.replace``)."""
    import os

    p = path or _state_path()
    tmp = p.with_suffix(p.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(snap.to_dict(), indent=2), encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


@dataclass
class UpstreamDiff:
    prev_commit: str
    new_commit: str
    new_skills: list[str] = field(default_factory=list)
    removed_skills: list[str] = field(default_factory=list)
    new_tools: list[str] = field(default_factory=list)
    removed_tools: list[str] = field(default_factory=list)

    def has_changes(self) -> bool:
        return bool(
            self.new_skills
            or self.removed_skills
            or self.new_tools
            or self.removed_tools
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_diff(
    previous: SkillsSnapshot | None, current: SkillsSnapshot
) -> UpstreamDiff:
    prev_skills = set(previous.skills) if previous else set()
    prev_tools = set(previous.tools) if previous else set()
    cur_skills = set(current.skills)
    cur_tools = set(current.tools)
    return UpstreamDiff(
        prev_commit=previous.commit if previous else "",
        new_commit=current.commit,
        new_skills=sorted(cur_skills - prev_skills),
        removed_skills=sorted(prev_skills - cur_skills),
        new_tools=sorted(cur_tools - prev_tools),
        removed_tools=sorted(prev_tools - cur_tools),
    )


def scan_upstream(
    *,
    skills_root: Path | None = None,
    state_path: Path | None = None,
    persist: bool = True,
) -> UpstreamDiff:
    """Return a diff between the last known snapshot and the current tree.

    Persists the new snapshot by default so subsequent calls only surface
    further changes.
    """
    current = take_snapshot(skills_root)
    prev = load_prev_snapshot(state_path)
    diff = compute_diff(prev, current)
    if persist:
        save_snapshot(current, state_path)
    return diff


def format_diff(diff: UpstreamDiff) -> str:
    if not diff.has_changes():
        return f"No new UiPath skills or tools (commit {diff.new_commit[:8] or 'unknown'})."
    lines: list[str] = []
    header = (
        f"Upstream skills changed: {diff.prev_commit[:8] or 'initial'} -> "
        f"{diff.new_commit[:8] or 'unknown'}"
    )
    lines.append(header)
    if diff.new_skills:
        lines.append("  new skills: " + ", ".join(diff.new_skills))
    if diff.removed_skills:
        lines.append("  removed skills: " + ", ".join(diff.removed_skills))
    if diff.new_tools:
        lines.append("  new tool packs: " + ", ".join(diff.new_tools))
    if diff.removed_tools:
        lines.append("  removed tool packs: " + ", ".join(diff.removed_tools))
    return "\n".join(lines)
