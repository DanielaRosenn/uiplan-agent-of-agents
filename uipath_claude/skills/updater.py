"""Skills submodule updater - keeps UiPath/skills in sync."""
from datetime import datetime, timezone
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import os

from uipath_claude.skills.manifest import (
    get_sync_manifest_path,
    load_sync_manifest,
    save_sync_manifest,
)


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
        env = os.environ.copy()
        if os.environ.get("UIPATH_GIT_SSL_NO_VERIFY", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            env["GIT_SSL_NO_VERIFY"] = "1"
        
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
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
    
    if current == remote:
        return False, f"Skills are up to date (commit {current})", current, remote
    
    return True, f"Updates available: {current} -> {remote}", current, remote


def update_skills(skills_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Update the skills submodule to the latest version.
    
    Returns:
        (success, message)
    """
    if skills_path is None:
        skills_path = get_skills_submodule_path()
    
    if not skills_path.exists():
        return False, "Skills submodule not found"
    
    previous_commit = get_current_commit(skills_path)

    stash_created = False
    had_local_changes = False

    # Check for local changes
    success, status = run_git_command(["status", "--porcelain"], skills_path)
    if success and status:
        had_local_changes = True
        stash_success, stash_output = run_git_command(
            ["stash", "push", "-u", "-m", "uipath-claude-auto-stash"],
            skills_path,
        )
        stash_created = stash_success and "No local changes to save" not in stash_output
    
    # Checkout main and pull
    success, output = run_git_command(["checkout", "main"], skills_path)
    if not success:
        return False, f"Failed to checkout main: {output}"
    
    success, output = run_git_command(["pull", "origin", "main"], skills_path)
    if not success:
        return False, f"Failed to pull: {output}"
    
    new_commit = get_current_commit(skills_path)
    warnings: list[str] = []
    sync_record = {
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
        "previous_commit": previous_commit,
        "current_commit": new_commit,
        "skills_path": str(skills_path.resolve()),
    }
    try:
        save_sync_manifest(sync_record)
    except Exception as exc:
        warnings.append(f"failed to write sync manifest: {exc}")

    if stash_created:
        pop_success, pop_output = run_git_command(["stash", "pop"], skills_path)
        if not pop_success:
            warnings.append(
                "stashed local changes could not be auto-restored "
                f"(possible conflicts): {pop_output}"
            )
    elif had_local_changes:
        warnings.append(
            "local changes were detected but not stashed automatically; "
            "verify working tree state"
        )

    if warnings:
        warning_text = "; ".join(warnings)
        return True, f"Skills updated to commit {new_commit} (warning: {warning_text})"
    return True, f"Skills updated to commit {new_commit}"


def get_sync_staleness(max_age_hours: int = 24) -> Tuple[bool, str]:
    """
    Check whether local sync metadata is missing or stale.

    Returns:
        (is_stale_or_missing, message)
    """
    manifest_path = get_sync_manifest_path()
    manifest = load_sync_manifest(manifest_path)
    if not manifest:
        return True, "Skills sync metadata is missing. Run /update-skills to create it."

    raw_timestamp = str(manifest.get("last_synced_at") or "").strip()
    if not raw_timestamp:
        return True, "Skills sync metadata is missing timestamp. Run /update-skills."

    try:
        last_synced_at = datetime.fromisoformat(raw_timestamp)
    except ValueError:
        return True, "Skills sync metadata timestamp is invalid. Run /update-skills."

    if last_synced_at.tzinfo is None:
        last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)

    age_hours = (datetime.now(timezone.utc) - last_synced_at.astimezone(timezone.utc)).total_seconds() / 3600
    if age_hours > max_age_hours:
        current_commit = manifest.get("current_commit") or "unknown"
        return (
            True,
            f"Skills sync metadata is stale ({age_hours:.1f}h old, commit {current_commit}). "
            "Run /update-skills.",
        )
    return False, ""


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
        "last_synced_at": None,
    }
    
    if not skills_path.exists():
        return info
    
    info["current_commit"] = get_current_commit(skills_path)
    info["remote_commit"] = get_remote_commit(skills_path)
    info["has_updates"] = (
        info["current_commit"] != info["remote_commit"]
        and info["remote_commit"] is not None
    )
    manifest = load_sync_manifest()
    info["last_synced_at"] = manifest.get("last_synced_at") if manifest else None
    
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
