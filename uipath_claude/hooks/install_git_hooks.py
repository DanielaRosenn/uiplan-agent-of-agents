"""Install git hooks that keep the ``skills/`` submodule always up to date.

Running this installs three tiny hooks into ``.git/hooks`` of the parent repo:

* ``post-merge``      — after ``git pull``
* ``post-checkout``   — after ``git checkout``
* ``post-rewrite``    — after ``git rebase`` or commit amends

Each hook simply invokes ``git submodule update --init --remote --merge`` for
the ``skills`` submodule (best-effort; stays quiet on failure so offline work
is never blocked).

Usage:
    python -m uipath_claude.hooks.install_git_hooks [--force]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HOOK_NAMES = ("post-merge", "post-checkout", "post-rewrite")

HOOK_MARKER = "# uipath-builder-agent: skills-autoupdate"

HOOK_SCRIPT = f"""#!/usr/bin/env bash
{HOOK_MARKER}
# Keep the skills/ submodule in sync with UiPath/skills upstream.
# Best-effort: never fail the host git operation.
set +e
if [ -f .gitmodules ] && grep -q 'path = skills' .gitmodules 2>/dev/null; then
    git submodule update --init --remote --merge skills >/dev/null 2>&1 || true
fi
exit 0
"""


def _repo_root(start: Path | None = None) -> Path | None:
    cur = (start or Path.cwd()).resolve()
    while cur != cur.parent:
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    return None


def _hooks_dir(repo_root: Path) -> Path:
    # Git supports both .git as dir and .git as file (worktrees); handle both.
    git_path = repo_root / ".git"
    if git_path.is_file():
        # Worktree — parse the gitdir line.
        try:
            line = git_path.read_text(encoding="utf-8").strip()
            if line.startswith("gitdir:"):
                gitdir = Path(line.split(":", 1)[1].strip())
                if not gitdir.is_absolute():
                    gitdir = (repo_root / gitdir).resolve()
                return gitdir / "hooks"
        except OSError:
            pass
    return git_path / "hooks"


def install(
    repo_root: Path | None = None,
    *,
    force: bool = False,
) -> list[tuple[str, str]]:
    """Install hooks; returns a list of ``(hook_name, status)`` tuples."""
    root = repo_root or _repo_root()
    if root is None:
        raise RuntimeError("Not inside a git repository")

    hooks_dir = _hooks_dir(root)
    hooks_dir.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, str]] = []
    for name in HOOK_NAMES:
        target = hooks_dir / name
        if target.exists():
            existing = target.read_text(encoding="utf-8", errors="ignore")
            if HOOK_MARKER in existing:
                results.append((name, "already installed"))
                continue
            if not force:
                results.append((name, "exists (skipped; use --force)"))
                continue
        target.write_text(HOOK_SCRIPT, encoding="utf-8", newline="\n")
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        results.append((name, "installed"))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing hooks")
    args = parser.parse_args(argv)
    try:
        results = install(force=args.force)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    for name, status in results:
        print(f"{name}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
