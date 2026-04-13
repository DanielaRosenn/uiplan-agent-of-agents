"""Test skill source path resolution."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from uipath_claude.skills.manifest import (
    get_sync_manifest_path,
    load_sync_manifest,
    save_sync_manifest,
)
from uipath_claude.skills.sources import build_skill_sources
from uipath_claude.skills.updater import get_sync_staleness, run_git_command, update_skills


def test_build_skill_sources_precedence(tmp_path, monkeypatch):
    """Test source order matches required precedence."""
    project_local = tmp_path / ".uipath-claude" / "skills"
    user_local = tmp_path / "home" / ".cursor" / "skills"
    official = tmp_path / "skills" / "skills"
    cato = tmp_path / "templates" / "long-running" / ".cursor" / "skills"

    project_local.mkdir(parents=True)
    user_local.mkdir(parents=True)
    official.mkdir(parents=True)
    cato.mkdir(parents=True)

    monkeypatch.setattr("uipath_claude.skills.sources.Path.home", lambda: tmp_path / "home")

    sources = build_skill_sources(tmp_path)
    assert sources[0] == str(project_local.resolve())
    assert sources[1] == str(user_local.resolve())
    assert sources[2] == str(official.resolve())
    assert str(cato.resolve()) in sources[3:]


def test_build_skill_sources_skips_missing_paths(tmp_path, monkeypatch):
    """Test non-existing source paths are ignored."""
    monkeypatch.setattr("uipath_claude.skills.sources.Path.home", lambda: tmp_path / "home")
    sources = build_skill_sources(tmp_path)
    assert sources == []


def test_sync_manifest_roundtrip(tmp_path):
    """Test sync metadata can be persisted and loaded."""
    manifest_path = tmp_path / ".uipath-claude" / "skills-sync-manifest.json"
    payload = {
        "last_synced_at": "2026-04-13T12:00:00+00:00",
        "previous_commit": "11111111",
        "current_commit": "22222222",
        "skills_path": str(tmp_path / "skills"),
    }

    written_path = save_sync_manifest(payload, path=manifest_path)
    loaded = load_sync_manifest(path=manifest_path)

    assert written_path == manifest_path
    assert loaded == payload


def test_get_sync_manifest_path_uses_explicit_project_root(tmp_path):
    """Explicit project root should be used directly."""
    project_root = tmp_path / "custom-root"
    project_root.mkdir(parents=True)

    manifest_path = get_sync_manifest_path(project_root=project_root)

    assert manifest_path == project_root / ".uipath-claude" / "skills-sync-manifest.json"


def test_get_sync_staleness_missing_manifest(monkeypatch):
    """Missing metadata should be treated as stale."""
    monkeypatch.setattr("uipath_claude.skills.updater.load_sync_manifest", lambda _path: None)

    is_stale, message = get_sync_staleness(max_age_hours=24)

    assert is_stale is True
    assert "missing" in message.lower()


def test_get_sync_staleness_invalid_timestamp(monkeypatch):
    """Invalid timestamp metadata should be treated as stale."""
    monkeypatch.setattr(
        "uipath_claude.skills.updater.load_sync_manifest",
        lambda _path: {"last_synced_at": "not-a-timestamp"},
    )

    is_stale, message = get_sync_staleness(max_age_hours=24)

    assert is_stale is True
    assert "invalid" in message.lower()


def test_get_sync_staleness_stale_timestamp(monkeypatch):
    """Old metadata should trigger stale warning."""
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=26)).isoformat()
    monkeypatch.setattr(
        "uipath_claude.skills.updater.load_sync_manifest",
        lambda _path: {"last_synced_at": stale_time, "current_commit": "abc12345"},
    )

    is_stale, message = get_sync_staleness(max_age_hours=24)

    assert is_stale is True
    assert "stale" in message.lower()


def test_get_sync_staleness_fresh_timestamp(monkeypatch):
    """Recent metadata should not trigger stale warning."""
    fresh_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    monkeypatch.setattr(
        "uipath_claude.skills.updater.load_sync_manifest",
        lambda _path: {"last_synced_at": fresh_time, "current_commit": "abc12345"},
    )

    is_stale, message = get_sync_staleness(max_age_hours=24)

    assert is_stale is False
    assert message == ""


def test_run_git_command_ssl_no_verify_is_opt_in(monkeypatch, tmp_path):
    """GIT_SSL_NO_VERIFY should only be set when explicitly requested."""
    captured_env: dict[str, str] = {}

    class DummyProcess:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_subprocess_run(*_args, **kwargs):
        captured_env.update(kwargs["env"])
        return DummyProcess()

    monkeypatch.delenv("UIPATH_GIT_SSL_NO_VERIFY", raising=False)
    monkeypatch.delenv("GIT_SSL_NO_VERIFY", raising=False)
    monkeypatch.setattr("uipath_claude.skills.updater.subprocess.run", fake_subprocess_run)

    success, _ = run_git_command(["status"], tmp_path)

    assert success is True
    assert captured_env.get("GIT_SSL_NO_VERIFY") is None


def test_run_git_command_ssl_no_verify_enabled_by_env(monkeypatch, tmp_path):
    """Opt-in env flag should enable SSL bypass for git."""
    captured_env: dict[str, str] = {}

    class DummyProcess:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_subprocess_run(*_args, **kwargs):
        captured_env.update(kwargs["env"])
        return DummyProcess()

    monkeypatch.setenv("UIPATH_GIT_SSL_NO_VERIFY", "1")
    monkeypatch.delenv("GIT_SSL_NO_VERIFY", raising=False)
    monkeypatch.setattr("uipath_claude.skills.updater.subprocess.run", fake_subprocess_run)

    success, _ = run_git_command(["status"], tmp_path)

    assert success is True
    assert captured_env.get("GIT_SSL_NO_VERIFY") == "1"


def test_update_skills_restores_stash_when_created(monkeypatch, tmp_path):
    """Successful update should restore auto-created stash."""
    skills_path = tmp_path / "skills"
    skills_path.mkdir(parents=True)
    calls: list[list[str]] = []

    def fake_run_git_command(args, _cwd):
        calls.append(args)
        if args == ["status", "--porcelain"]:
            return True, " M file.txt"
        if args[:2] == ["stash", "push"]:
            return True, "Saved working directory and index state"
        if args == ["checkout", "main"]:
            return True, "ok"
        if args == ["pull", "origin", "main"]:
            return True, "ok"
        if args == ["stash", "pop"]:
            return True, "Applied stash"
        return True, "ok"

    monkeypatch.setattr("uipath_claude.skills.updater.run_git_command", fake_run_git_command)
    monkeypatch.setattr("uipath_claude.skills.updater.get_current_commit", lambda _p: "abc12345")
    monkeypatch.setattr("uipath_claude.skills.updater.save_sync_manifest", lambda _m: skills_path)

    success, message = update_skills(skills_path=skills_path)

    assert success is True
    assert "updated to commit" in message.lower()
    assert ["stash", "pop"] in calls


def test_update_skills_reports_stash_pop_conflict(monkeypatch, tmp_path):
    """Stash pop conflict should be surfaced as warning, not silent success."""
    skills_path = tmp_path / "skills"
    skills_path.mkdir(parents=True)

    def fake_run_git_command(args, _cwd):
        if args == ["status", "--porcelain"]:
            return True, " M file.txt"
        if args[:2] == ["stash", "push"]:
            return True, "Saved working directory and index state"
        if args == ["checkout", "main"]:
            return True, "ok"
        if args == ["pull", "origin", "main"]:
            return True, "ok"
        if args == ["stash", "pop"]:
            return False, "CONFLICT (content): Merge conflict in file.txt"
        return True, "ok"

    monkeypatch.setattr("uipath_claude.skills.updater.run_git_command", fake_run_git_command)
    monkeypatch.setattr("uipath_claude.skills.updater.get_current_commit", lambda _p: "abc12345")
    monkeypatch.setattr("uipath_claude.skills.updater.save_sync_manifest", lambda _m: skills_path)

    success, message = update_skills(skills_path=skills_path)

    assert success is True
    assert "warning" in message.lower()
    assert "could not be auto-restored" in message

