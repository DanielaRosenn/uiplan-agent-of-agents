"""Unit tests for publish_project (process + maestro)."""
from __future__ import annotations

import subprocess
from unittest.mock import patch

from uipath_claude.tools import deploy_tool


def _run(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _mk_project(tmp_path, name="Proj"):
    pdir = tmp_path / name
    pdir.mkdir()
    (pdir / "project.json").write_text("{}", encoding="utf-8")
    return pdir


def test_publish_project_process_runs_solution_pack_then_publish(tmp_path, monkeypatch):
    pdir = _mk_project(tmp_path)
    out_dir = tmp_path / "_packages"
    out_dir.mkdir(parents=True, exist_ok=True)
    nupkg = out_dir / "Proj.1.0.0.nupkg"
    nupkg.write_text("x", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text, timeout, cwd=None):
        calls.append(cmd)
        if "pack" in cmd:
            return _run(0, stdout=str(nupkg))
        if "publish" in cmd:
            return _run(0, stdout='{"ok":true}')
        return _run(1, stderr="unexpected")

    monkeypatch.setattr(deploy_tool.subprocess, "run", fake_run)
    monkeypatch.setattr(deploy_tool.shutil, "which", lambda _: "uip")

    result = deploy_tool.publish_project(str(pdir), project_type="process")

    assert result["status"] == "ok", result
    assert result["package_path"] == str(nupkg)
    assert calls[0][1:3] == ["solution", "pack"]
    assert calls[1][1:3] == ["solution", "publish"]


def test_publish_project_maestro_runs_flow_pack_then_solution_publish(tmp_path, monkeypatch):
    pdir = _mk_project(tmp_path, "FlowProj")
    out_dir = tmp_path / "_packages"
    out_dir.mkdir(parents=True, exist_ok=True)
    nupkg = out_dir / "FlowProj.1.0.0.nupkg"
    nupkg.write_text("x", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(cmd, capture_output, text, timeout, cwd=None):
        calls.append(cmd)
        if cmd[1:3] == ["flow", "pack"]:
            return _run(0, stdout=f"Packed -> {nupkg}")
        if cmd[1:3] == ["solution", "publish"]:
            return _run(0, stdout='{"ok":true}')
        return _run(1, stderr="unexpected")

    monkeypatch.setattr(deploy_tool.subprocess, "run", fake_run)
    monkeypatch.setattr(deploy_tool.shutil, "which", lambda _: "uip")

    result = deploy_tool.publish_project(str(pdir), project_type="maestro")

    assert result["status"] == "ok", result
    assert result["package_path"] == str(nupkg)
    assert calls[0][1:3] == ["flow", "pack"]
    assert calls[1][1:3] == ["solution", "publish"]


def test_publish_project_pack_failure_short_circuits(tmp_path, monkeypatch):
    pdir = _mk_project(tmp_path)

    def fake_run(cmd, capture_output, text, timeout, cwd=None):
        return _run(1, stderr="pack boom")

    monkeypatch.setattr(deploy_tool.subprocess, "run", fake_run)
    monkeypatch.setattr(deploy_tool.shutil, "which", lambda _: "uip")

    result = deploy_tool.publish_project(str(pdir), project_type="process")
    assert result["status"] == "failed"
    assert result.get("stage") == "pack"
