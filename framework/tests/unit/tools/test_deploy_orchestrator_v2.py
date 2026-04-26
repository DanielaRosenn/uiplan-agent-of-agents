"""Unit tests for deploy_to_orchestrator_v2 and env-config helper."""
from __future__ import annotations

import json
import subprocess

from uipath_claude.tools import deploy_tool


def _run(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _publish_ok(**_kw):
    return {"status": "ok", "package_path": "/tmp/p.nupkg", "publish": {}}


def test_deploy_v2_calls_publish_then_processes_create(tmp_path, monkeypatch):
    pdir = tmp_path / "ProjA"
    pdir.mkdir()
    (pdir / "project.json").write_text("{}", encoding="utf-8")

    captured: list[list[str]] = []

    def fake_run(cmd, capture_output, text, timeout, cwd=None):
        captured.append(cmd)
        return _run(0, stdout=json.dumps({"Key": "PROC-XYZ"}))

    monkeypatch.setattr(deploy_tool, "publish_project", _publish_ok)
    monkeypatch.setattr(deploy_tool.subprocess, "run", fake_run)
    monkeypatch.setattr(deploy_tool.shutil, "which", lambda _: "uip")

    out = deploy_tool.deploy_to_orchestrator_v2(
        project_dir=str(pdir),
        project_type="process",
        folder="Dev",
        process_name="MyProc",
    )

    assert out["status"] == "ok"
    assert out["process_key"] == "PROC-XYZ"
    assert captured[0][1:4] == ["or", "processes", "create"]
    assert "MyProc" in captured[0]
    assert "--folder" in captured[0] and "Dev" in captured[0]


def test_deploy_v2_maestro_uses_flow_process_create(tmp_path, monkeypatch):
    pdir = tmp_path / "FlowProj"
    pdir.mkdir()

    captured: list[list[str]] = []

    def fake_run(cmd, capture_output, text, timeout, cwd=None):
        captured.append(cmd)
        return _run(0, stdout="{}")

    monkeypatch.setattr(deploy_tool, "publish_project", _publish_ok)
    monkeypatch.setattr(deploy_tool.subprocess, "run", fake_run)
    monkeypatch.setattr(deploy_tool.shutil, "which", lambda _: "uip")

    out = deploy_tool.deploy_to_orchestrator_v2(
        project_dir=str(pdir),
        project_type="maestro",
        folder="Dev",
        process_name="FlowProc",
    )

    assert out["status"] == "ok"
    assert captured[0][1:4] == ["flow", "process", "create"]


def test_deploy_v2_failure_in_publish_short_circuits(tmp_path, monkeypatch):
    pdir = tmp_path / "P"
    pdir.mkdir()

    monkeypatch.setattr(
        deploy_tool, "publish_project", lambda **_kw: {"status": "failed", "error": "no nupkg"}
    )
    called = {"run": False}

    def fake_run(*_a, **_kw):
        called["run"] = True
        return _run(0)

    monkeypatch.setattr(deploy_tool.subprocess, "run", fake_run)

    out = deploy_tool.deploy_to_orchestrator_v2(project_dir=str(pdir), folder="Dev")
    assert out["status"] == "failed"
    assert out["stage"] == "publish"
    assert called["run"] is False


def test_deploy_v2_blocks_shared_without_human_approval(tmp_path):
    pdir = tmp_path / "P"
    pdir.mkdir()

    out = deploy_tool.deploy_to_orchestrator_v2(project_dir=str(pdir), folder="Shared")

    assert out["status"] == "failed"
    assert out["stage"] == "policy"
    assert "human approval" in out["error"]


def test_deploy_v2_blocks_production_even_with_approval(tmp_path):
    pdir = tmp_path / "P"
    pdir.mkdir()

    out = deploy_tool.deploy_to_orchestrator_v2(
        project_dir=str(pdir),
        folder="Production",
        human_confirmed=True,
        approved_by="ops",
    )

    assert out["status"] == "failed"
    assert out["stage"] == "policy"
    assert "Production" in out["error"]


def test_publish_runs_preflight_before_pack(tmp_path, monkeypatch):
    pdir = tmp_path / "Proj"
    pdir.mkdir()
    (pdir / "project.json").write_text("{}", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(args, cwd=None, timeout=600):
        calls.append(args)
        if args[:2] == ["solution", "pack"]:
            out_dir = pdir.parent / "_packages"
            out_dir.mkdir(exist_ok=True)
            (out_dir / "Proj.1.0.0.nupkg").write_text("pkg", encoding="utf-8")
        return {"status": "ok", "stdout": "", "stderr": "", "cmd": ["uip", *args]}

    monkeypatch.setattr(deploy_tool, "_run_uip", fake_run)

    out = deploy_tool.publish_project(str(pdir), folder_path="Dev")

    assert out["status"] == "ok"
    assert calls[0][:2] == ["solution", "restore"]
    assert calls[1][:2] == ["rpa", "analyze"]
    assert calls[2][:2] == ["solution", "pack"]
    assert calls[3][:2] == ["solution", "publish"]


def test_get_deployment_config_uses_default_folder_fallback(monkeypatch):
    monkeypatch.setenv("UIPATH_ORCHESTRATOR_URL", "https://x")
    monkeypatch.setenv("UIPATH_TENANT_NAME", "T")
    monkeypatch.delenv("UIPATH_FOLDER_PATH", raising=False)
    monkeypatch.setenv("UIPATH_DEFAULT_FOLDER", "MyFallback")

    cfg = deploy_tool.get_deployment_config_from_env()
    assert cfg["success"] is True
    assert cfg["folder_path"] == "MyFallback"


def test_get_deployment_config_prefers_folder_path_over_default(monkeypatch):
    monkeypatch.setenv("UIPATH_ORCHESTRATOR_URL", "https://x")
    monkeypatch.setenv("UIPATH_TENANT_NAME", "T")
    monkeypatch.setenv("UIPATH_FOLDER_PATH", "Explicit")
    monkeypatch.setenv("UIPATH_DEFAULT_FOLDER", "Fallback")

    cfg = deploy_tool.get_deployment_config_from_env()
    assert cfg["folder_path"] == "Explicit"
