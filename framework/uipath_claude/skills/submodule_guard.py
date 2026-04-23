"""Submodule guard for the UiPath/skills submodule.

Enforces that ``skills/`` is:

- checked out at a commit present in ``.uipath/skills-approved.sha``,
- clean (no local modifications),
- consistent with the skills referenced in rule files (``CLAUDE.md``,
  ``docs/uipath-cli.md``, ``docs/uipath-workflows.md``,
  ``.cursor/rules/uipath.mdc``, ``.cursorrules``), and
- referenced CLI verbs in ``docs/uipath-cli.md`` are in the live-verified
  allow-list at ``docs/uipath-cli.verbs.json``.

Run as a module (``python -m uipath_claude.skills.submodule_guard``) from git
hooks, CI, or the session-start hook. Non-zero exit on any violation unless
``UIPATH_GUARD_MODE=warn``.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from uipath_claude.skills.updater import (
    get_skills_submodule_path,
    run_git_command,
)


APPROVED_SHA_RELATIVE = Path(".uipath") / "skills-approved.sha"
VERBS_FILE_RELATIVE = Path("docs") / "uipath-cli.verbs.json"
RULE_FILES_RELATIVE: tuple[Path, ...] = (
    Path("CLAUDE.md"),
    Path("docs") / "uipath-cli.md",
    Path("docs") / "uipath-workflows.md",
    Path(".cursor") / "rules" / "uipath.mdc",
    Path(".cursorrules"),
)

_SKILL_ID_PATTERN = re.compile(r"\buipath-[a-z0-9][a-z0-9-]*\b")


@dataclass
class GuardResult:
    """Outcome of a guard run.

    ``errors`` are blocking, ``warnings`` are informational.
    """

    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.ok = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_report(self) -> str:
        lines: list[str] = []
        status = "OK" if self.ok else "FAIL"
        lines.append(f"submodule-guard: {status}")
        if self.checked:
            lines.append("  checks:")
            for c in self.checked:
                lines.append(f"    - {c}")
        if self.warnings:
            lines.append("  warnings:")
            for w in self.warnings:
                lines.append(f"    - {w}")
        if self.errors:
            lines.append("  errors:")
            for e in self.errors:
                lines.append(f"    - {e}")
        return "\n".join(lines)


def _repo_root() -> Path:
    """Locate the repository root (the directory containing ``.git``)."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent.parent


def _read_approved_shas(path: Path) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _list_installed_skills(skills_root: Path) -> set[str]:
    skills_dir = skills_root / "skills"
    if not skills_dir.exists():
        return set()
    return {
        d.name
        for d in skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    }


def _iter_fenced_command_lines(text: str) -> Iterable[str]:
    """Yield command lines from fenced code blocks that look like shell."""
    in_fence = False
    fence_lang = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            if in_fence:
                in_fence = False
                fence_lang = ""
            else:
                in_fence = True
                fence_lang = stripped[3:].strip().lower()
            continue
        if not in_fence:
            continue
        if fence_lang and fence_lang not in {
            "bash",
            "sh",
            "shell",
            "zsh",
            "pwsh",
            "powershell",
            "",
            "console",
            "yaml",
            "yml",
        }:
            continue
        yield raw


def _extract_verb_usages(text: str) -> list[tuple[str, str]]:
    """Extract ``(cli, verb)`` pairs mentioned in ``cli verb [sub]`` command form.

    Only looks at fenced blocks to avoid false positives from prose. Captures
    the first and second tokens after the CLI name so we can match against
    multi-word verbs like ``package analyze`` or ``solution deploy-activate``.
    """
    usages: list[tuple[str, str]] = []
    clis = {"uipcli", "uipath", "uip"}
    for line in _iter_fenced_command_lines(text):
        stripped = line.lstrip()
        # Skip comment lines - they're inline annotations, not command syntax.
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        # Strip common PS / bash prompt / continuation noise
        stripped = stripped.lstrip("$> ").rstrip("\\").rstrip("`").rstrip()
        tokens = stripped.split()
        if not tokens:
            continue
        # Find the CLI token (may be prefixed with e.g. ``uv run``).
        cli_index = -1
        for idx, tok in enumerate(tokens):
            if tok in clis:
                cli_index = idx
                break
        if cli_index == -1:
            continue
        cli = tokens[cli_index]
        tail = tokens[cli_index + 1 :]
        # Stop at inline shell comment markers.
        comment_idx = next(
            (i for i, t in enumerate(tail) if t.startswith("#") or t.startswith("//")),
            None,
        )
        if comment_idx is not None:
            tail = tail[:comment_idx]
        remainder = [t for t in tail if not t.startswith("-")]
        if not remainder:
            continue
        verb1 = remainder[0]
        verb2 = remainder[1] if len(remainder) > 1 else ""
        usages.append((cli, f"{verb1} {verb2}".strip()))
    return usages


def _load_verb_allowlist(path: Path) -> dict[str, set[str]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, set[str]] = {}
    clis = data.get("clis", {})
    if not isinstance(clis, dict):
        return {}
    for cli, spec in clis.items():
        verbs = spec.get("verbs", []) if isinstance(spec, dict) else []
        out[cli] = {v.strip() for v in verbs if isinstance(v, str)}
    return out


def _verb_allowed(cli: str, verb: str, allow: dict[str, set[str]]) -> bool:
    """Check whether ``verb`` (up to two tokens) is allow-listed for ``cli``.

    An allow-list entry may be one token (``auth``) or two tokens
    (``package pack``). Match by checking whether any allow-listed entry is a
    prefix of the observed verb.
    """
    allowed = allow.get(cli)
    if not allowed:
        return True  # No allow-list for this CLI -> don't block.
    for entry in allowed:
        if verb == entry or verb.startswith(entry + " "):
            return True
        # Single-token observation vs single-token allow entry.
        if " " not in entry and verb.split()[0] == entry:
            return True
    return False


def _referenced_skill_ids(text: str) -> set[str]:
    # Ignore inline code blocks that say ``uipath-agent-framework`` etc. - we
    # are purely checking references to skills in the catalog; any hit that
    # does not match a real skill and is not a known non-skill token is an
    # error.
    ids = set(_SKILL_ID_PATTERN.findall(text))
    # Strip common non-skill names that follow the ``uipath-*`` pattern.
    non_skill_prefixes = {
        "uipath-python",
        "uipath-langchain",
        "uipath-langchain-python",
        "uipath-llamaindex",
        "uipath-agent-framework",
        "uipath-integrations-python",
        "uipath-typescript",
        "uipath-builder-agent",
        "uipath-claude",
        "uipath-claude-code",
        "uipath-spec-project-template",
        "uipath-project-discovery-agent",
        "uipath-autopilot",
        "uipath-cli",
        "uipath-cli-tasks",
        "uipath-cli-linux",
        "uipath-cli-windows",
        "uipath-cli-macos",
        "uipath-workflows",
        "uipath-docs",
        "uipath-feedback-send",
        "uipath-policy",
    }
    return {i for i in ids if i not in non_skill_prefixes}


def verify(strict: bool = True, repo_root: Path | None = None) -> GuardResult:
    """Run the guard and return a ``GuardResult``.

    ``strict`` controls whether missing optional files (e.g., the approved
    SHA file) are errors. Defaults to strict.
    """
    result = GuardResult()
    root = (repo_root or _repo_root()).resolve()

    skills_path = get_skills_submodule_path()
    if not skills_path.is_absolute():
        skills_path = (root / skills_path).resolve()

    # 1. Submodule presence + registration.
    gitmodules = root / ".gitmodules"
    if not gitmodules.exists():
        result.add_error(".gitmodules missing at repo root")
    else:
        gm_text = gitmodules.read_text(encoding="utf-8", errors="replace")
        if "UiPath/skills" not in gm_text and "uipath/skills" not in gm_text.lower():
            result.add_error(
                ".gitmodules does not register the UiPath/skills submodule"
            )
    result.checked.append(".gitmodules")

    if not skills_path.exists() or not (skills_path / "SKILL.md").exists() \
            and not (skills_path / "CLAUDE.md").exists():
        # Lack of SKILL.md at top is expected; only the submodule directory
        # must exist with *some* content.
        if not skills_path.exists():
            result.add_error(f"skills submodule directory missing: {skills_path}")
            return result
    result.checked.append("skills/ submodule directory present")

    # 2. HEAD commit vs approved allow-list.
    approved_file = root / APPROVED_SHA_RELATIVE
    approved = _read_approved_shas(approved_file)
    if not approved:
        if strict:
            result.add_error(
                f"{APPROVED_SHA_RELATIVE} missing or empty; "
                "seed it with the approved submodule commit SHA(s)."
            )
        else:
            result.add_warning(f"{APPROVED_SHA_RELATIVE} missing or empty")
    ok, head = run_git_command(["rev-parse", "HEAD"], skills_path)
    if not ok:
        result.add_error(f"cannot read skills submodule HEAD: {head}")
    else:
        head = head.strip()
        if approved:
            matched = any(
                head == sha or head.startswith(sha) or sha.startswith(head)
                for sha in approved
            )
            if not matched:
                result.add_error(
                    f"skills submodule HEAD {head[:12]} is not in "
                    f"{APPROVED_SHA_RELATIVE}. Either revert or append the "
                    "new SHA after reviewing the changes."
                )
        result.checked.append(f"skills HEAD = {head[:12]}")

    # 3. Clean working tree.
    ok, status_out = run_git_command(
        ["status", "--porcelain"], skills_path,
    )
    if not ok:
        result.add_error(f"cannot check skills working tree: {status_out}")
    elif status_out.strip():
        result.add_error(
            "skills submodule has local modifications (run "
            "`git -C skills checkout .` or commit upstream)."
        )
    result.checked.append("skills working tree clean")

    # 4. Rule files reference only installed skills.
    installed = _list_installed_skills(skills_path)
    for rel in RULE_FILES_RELATIVE:
        path = root / rel
        if not path.exists():
            result.add_warning(f"rule file missing: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        referenced = _referenced_skill_ids(text)
        missing = sorted(s for s in referenced if s not in installed)
        if missing:
            result.add_error(
                f"{rel} references unknown skill id(s): {', '.join(missing)}"
            )
        result.checked.append(f"skill refs in {rel}")

    # 5. CLI verb usages in docs/uipath-cli.md are on the allow-list.
    cli_doc = root / "docs" / "uipath-cli.md"
    verbs_file = root / VERBS_FILE_RELATIVE
    allow = _load_verb_allowlist(verbs_file)
    if cli_doc.exists() and allow:
        usages = _extract_verb_usages(cli_doc.read_text(encoding="utf-8", errors="replace"))
        bad: list[str] = []
        for cli, verb in usages:
            if not _verb_allowed(cli, verb, allow):
                bad.append(f"{cli} {verb}")
        # De-duplicate while preserving order.
        seen: set[str] = set()
        unique_bad = [b for b in bad if not (b in seen or seen.add(b))]
        if unique_bad:
            result.add_error(
                "docs/uipath-cli.md references CLI verbs not in "
                f"{VERBS_FILE_RELATIVE}: {', '.join(unique_bad)}"
            )
        result.checked.append("CLI verbs in docs/uipath-cli.md")
    elif cli_doc.exists() and not allow:
        result.add_warning(
            f"{VERBS_FILE_RELATIVE} missing or empty; skipping verb scan."
        )

    return result


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Enforce that the skills/ submodule is pinned to an approved "
            "commit and rule files reference only existing skills/verbs."
        )
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Fail on missing approved-SHA file (default).",
    )
    parser.add_argument(
        "--warn",
        dest="strict",
        action="store_false",
        help="Treat missing artifacts as warnings (used for bootstrap runs).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a text report.",
    )
    args = parser.parse_args()

    result = verify(strict=args.strict)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "checked": result.checked,
                },
                indent=2,
            )
        )
    else:
        print(result.to_report())

    mode = os.environ.get("UIPATH_GUARD_MODE", "block").lower()
    if result.ok:
        return 0
    return 0 if mode == "warn" else 1


if __name__ == "__main__":
    sys.exit(_cli())
