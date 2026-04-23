"""Tests for the documentation library seed script."""
import os
import subprocess
import sys
from pathlib import Path


def test_seed_script_does_not_create_cache_inside_book(tmp_path, monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(tmp_path))
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "ops" / "scripts" / "seed_uipath_docs.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env={**os.environ, "UIPATH_CLAUDE_LIBRARY": str(tmp_path)},
        cwd=str(repo_root),
    )
    assert result.returncode == 0, result.stderr

    cache_dirs = list(tmp_path.rglob("_cache"))
    assert cache_dirs == [], f"seed created cache dir(s) inside library: {cache_dirs}"


def test_seed_script_target_flag_overrides_env(tmp_path):
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "ops" / "scripts" / "seed_uipath_docs.py"
    target = tmp_path / "custom"

    result = subprocess.run(
        [sys.executable, str(script), "--target", str(target)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert result.returncode == 0, result.stderr
    assert (target / "catalog.yaml").exists()
