"""Skills submodule updater - keeps UiPath/skills in sync."""
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple


def get_skills_submodule_path() -> Path:
    """Get the path to the skills submodule."""
    # Find the repo root (where .git is)
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current / "skills"
        current = current.parent
    # Fallback to relative path from this file
    return Path(__file__).resolve().parent.parent.parent / "skills"


def run_git_command(args: list[str], cwd: Path) -> Tuple[bool, str]:
    """Run a git command and return (success, output)."""
    try:
        # Disable SSL verification for corporate proxies
        env = os.environ.copy()
        env["GIT_SSL_NO_VERIFY"] = "1"
        
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            # Do not inherit stdin: git may read prompts/credentials from it and can
            # consume buffered lines intended for Rich/CLI tests (e.g. CliRunner input).
            stdin=subprocess.DEVNULL,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Git command timed out"
    except FileNotFoundError:
        return False, "Git not found in PATH"
    except Exception as e:
        return False, str(e)


def get_current_commit(skills_path: Path) -> Optional[str]:
    """Get the current commit hash of the skills submodule."""
    success, output = run_git_command(["rev-parse", "HEAD"], skills_path)
    return output[:8] if success else None


def get_remote_commit(skills_path: Path, branch: str = "main") -> Optional[str]:
    """Get the latest commit hash from the remote."""
    # Fetch first
    run_git_command(["fetch", "origin", branch], skills_path)
    success, output = run_git_command(["rev-parse", f"origin/{branch}"], skills_path)
    return output[:8] if success else None


def check_for_updates(skills_path: Optional[Path] = None) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """
    Check if skills submodule has updates available.
    
    Returns:
        (has_updates, message, current_commit, remote_commit)
    """
    if skills_path is None:
        skills_path = get_skills_submodule_path()
    
    if not skills_path.exists():
        return False, "Skills submodule not found", None, None
    
    if not (skills_path / ".git").exists() and not (skills_path / "SKILL.md").exists():
        # Check if it's a submodule (has .git file pointing to parent)
        git_file = skills_path / ".git"
        if not git_file.exists():
            return False, "Skills directory is not a git repository", None, None
    
    current = get_current_commit(skills_path)
    if not current:
        return False, "Could not get current commit", None, None
    
    remote = get_remote_commit(skills_path)
    if not remote:
        return False, "Could not fetch remote (network issue?)", current, None
    
    # If the working tree is dirty, treat it as needing an update so that
    # ``ensure_fresh`` triggers the force-reset path in ``update_skills``.
    ok_status, status = run_git_command(["status", "--porcelain"], skills_path)
    dirty = bool(ok_status and status)

    if current == remote and not dirty:
        return False, f"Skills are up to date (commit {current})", current, remote

    suffix = " (dirty working tree)" if dirty else ""
    return True, f"Updates available: {current} -> {remote}{suffix}", current, remote


def update_skills(
    skills_path: Optional[Path] = None,
    *,
    force: bool = True,
) -> Tuple[bool, str]:
    """Update the skills submodule to the latest version.

    When ``force`` is ``True`` (default), local drift in the submodule is
    preserved on a timestamped backup branch and then the working tree is
    hard-reset to ``origin/main``. This guarantees the submodule is never
    left "dirty" in a way that blocks future auto-refreshes.

    Returns:
        (success, message)
    """
    import time as _time

    if skills_path is None:
        skills_path = get_skills_submodule_path()

    if not skills_path.exists():
        return False, "Skills submodule not found"

    # Fetch latest first (non-fatal if offline).
    run_git_command(["fetch", "origin", "main"], skills_path)

    success, status = run_git_command(["status", "--porcelain"], skills_path)
    notes: list[str] = []
    if success and status:
        if force:
            # Preserve local drift on a backup branch before resetting.
            backup = f"backup/local-{int(_time.time())}"
            run_git_command(["branch", backup], skills_path)
            run_git_command(["reset", "--hard", "HEAD"], skills_path)
            run_git_command(["clean", "-fd"], skills_path)
            notes.append(f"preserved local drift on branch {backup}")
        else:
            run_git_command(["stash", "push", "-m", "auto-stash by update_skills"], skills_path)
            notes.append("stashed local drift")

    # Check out main, then hard-reset to origin/main so we always match upstream.
    success, output = run_git_command(["checkout", "main"], skills_path)
    if not success:
        return False, f"Failed to checkout main: {output}"

    if force:
        success, output = run_git_command(["reset", "--hard", "origin/main"], skills_path)
        if not success:
            return False, f"Failed to reset to origin/main: {output}"
    else:
        success, output = run_git_command(["pull", "--ff-only", "origin", "main"], skills_path)
        if not success:
            return False, f"Failed to pull: {output}"

    new_commit = get_current_commit(skills_path)
    msg = f"Skills updated to commit {new_commit}"
    if notes:
        msg += " (" + "; ".join(notes) + ")"
    return True, msg


def _default_marker_path() -> Path:
    return get_skills_submodule_path().parent / ".skills_refresh_at"


def _default_session_marker_path() -> Path:
    return get_skills_submodule_path().parent / ".skills_session_refresh"


def ensure_fresh(
    marker_path: Path | None = None,
    max_age_seconds: int = 6 * 3600,
) -> str:
    """Refresh the skills submodule at most once per ``max_age_seconds``.

    Safe to call on CLI/MCP startup. Soft-fails on any network/git error so
    offline use is never blocked.
    """
    marker = marker_path or _default_marker_path()
    now = int(time.time())
    try:
        last = int(marker.read_text()) if marker.exists() else 0
    except (OSError, ValueError):
        last = 0

    if now - last < max_age_seconds:
        return "skipped: recent"

    has_updates, message, _cur, _rem = check_for_updates()
    if not has_updates:
        try:
            marker.write_text(str(now))
        except OSError:
            pass
        return f"skipped: {message}"

    ok, result = update_skills()
    try:
        marker.write_text(str(now))
    except OSError:
        pass
    return ("updated: " if ok else "failed: ") + result


def ensure_fresh_for_session(
    session_id: str,
    marker_path: Path | None = None,
) -> str:
    """Refresh the skills submodule at most once per ``session_id``.

    Stores the last-seen session id in ``<repo>/.skills_session_refresh``
    (JSON). If the stored id matches, returns early; otherwise force-syncs
    the submodule and atomically updates the marker. Soft-fails on all
    errors so offline use is never blocked.
    """
    import os as _os

    marker = marker_path or _default_session_marker_path()
    prev_id = ""
    if marker.exists():
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
            prev_id = str(data.get("session_id", ""))
        except (OSError, ValueError):
            prev_id = ""

    if session_id and prev_id == session_id:
        return "skipped: same session"

    has_updates, message, _cur, _rem = check_for_updates()
    if not has_updates:
        _write_session_marker(marker, session_id)
        return f"skipped: {message}"

    ok, result = update_skills()
    _write_session_marker(marker, session_id)
    return ("updated: " if ok else "failed: ") + result


def _write_session_marker(marker: Path, session_id: str) -> None:
    import os as _os

    tmp = marker.with_suffix(marker.suffix + ".tmp")
    try:
        tmp.write_text(
            json.dumps({"session_id": session_id}), encoding="utf-8"
        )
        _os.replace(tmp, marker)
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def get_skills_info(skills_path: Optional[Path] = None) -> dict:
    """Get information about the skills submodule."""
    if skills_path is None:
        skills_path = get_skills_submodule_path()
    
    info = {
        "path": str(skills_path),
        "exists": skills_path.exists(),
        "current_commit": None,
        "remote_commit": None,
        "has_updates": False,
        "skills_count": 0,
        "skills": [],
    }
    
    if not skills_path.exists():
        return info
    
    info["current_commit"] = get_current_commit(skills_path)
    info["remote_commit"] = get_remote_commit(skills_path)
    info["has_updates"] = (
        info["current_commit"] != info["remote_commit"]
        and info["remote_commit"] is not None
    )
    
    # Count skills
    skills_dir = skills_path / "skills"
    if skills_dir.exists():
        skills = [
            d.name for d in skills_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        ]
        info["skills"] = sorted(skills)
        info["skills_count"] = len(skills)
    
    return info
