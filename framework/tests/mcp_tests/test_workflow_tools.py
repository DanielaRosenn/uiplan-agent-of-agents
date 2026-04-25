"""MCP workflow tools: registry + dispatch with fakes (no uip CLI / no gate writes)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

import mcp_server.tools.workflow_tools as wt
from mcp_server.tools.workflow_tools import call_workflow_tool, get_workflow_tools


def test_workflow_tool_registry_count():
    names = {t.name for t in get_workflow_tools()}
    assert len(names) == 17
    assert all(n.startswith("uipath_workflow_") for n in names)


@pytest.mark.asyncio
async def test_unknown_tool_raises():
    with pytest.raises(ValueError, match="Unknown workflow tool"):
        await call_workflow_tool("uipath_workflow_nope", {})


@pytest.mark.asyncio
async def test_read_file_happy(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    out = await call_workflow_tool(
        "uipath_workflow_read_file", {"file_path": str(f)}
    )
    assert "hello" in str(out)


@pytest.mark.asyncio
async def test_read_file_missing_key():
    with pytest.raises(KeyError):
        await call_workflow_tool("uipath_workflow_read_file", {})


@pytest.mark.asyncio
async def test_list_directory_happy(tmp_path):
    (tmp_path / "x.txt").write_text("a", encoding="utf-8")
    out = await call_workflow_tool(
        "uipath_workflow_list_directory",
        {"directory_path": str(tmp_path), "pattern": "*.txt"},
    )
    assert isinstance(out, str)
    assert "x.txt" in out or "x" in out.lower()


@pytest.mark.asyncio
async def test_list_directory_missing_directory_path():
    with pytest.raises(KeyError):
        await call_workflow_tool("uipath_workflow_list_directory", {})


@pytest.mark.asyncio
async def test_read_project_happy(tmp_path):
    import json as _json

    (tmp_path / "project.json").write_text(
        _json.dumps({"name": "Demo"}), encoding="utf-8"
    )
    out = await call_workflow_tool(
        "uipath_workflow_read_project", {"project_dir": str(tmp_path)}
    )
    text = str(out)
    assert "Demo" in text
    assert "[OK]" in text or "{" in text


@pytest.mark.asyncio
async def test_ensure_project_with_name(tmp_path):
    out = await call_workflow_tool(
        "uipath_workflow_ensure_project",
        {"project_dir": str(tmp_path), "project_name": "SubProj"},
    )
    assert isinstance(out, str)
    assert (tmp_path / "SubProj").is_dir()


@pytest.mark.asyncio
async def test_write_file_blocked_by_design_gate(monkeypatch):
    monkeypatch.setattr(
        wt,
        "_design_block_or_text",
        lambda *a, **k: "[BLOCKED] design",
    )
    out = await call_workflow_tool(
        "uipath_workflow_write_file",
        {"file_path": "Main.xaml", "content": "<x/>"},
    )
    assert "[BLOCKED]" in str(out)


@pytest.mark.asyncio
async def test_write_file_happy_when_gates_clear(monkeypatch):
    monkeypatch.setattr(wt, "_design_block_or_text", lambda *a, **k: None)
    monkeypatch.setattr(wt, "_maybe_mark_dirty_after_write", lambda *a, **k: None)

    class _Inv:
        def invoke(self, payload):
            return f"[OK] wrote {payload['file_path']}"

    monkeypatch.setattr(wt, "_write_file", _Inv())
    out = await call_workflow_tool(
        "uipath_workflow_write_file",
        {"file_path": "foo.txt", "content": "body"},
    )
    assert str(out).startswith("[OK]")


@pytest.mark.asyncio
async def test_install_package_respects_session_gate(monkeypatch):
    monkeypatch.setattr(wt, "_design_block_or_text", lambda *a, **k: None)
    monkeypatch.setattr(
        wt,
        "_gate_block_or_text",
        lambda *a, **k: "[BLOCKED] verify first",
    )
    out = await call_workflow_tool(
        "uipath_workflow_install_package",
        {
            "project_dir": "/tmp/proj",
            "package_id": "UiPath.System.Activities",
        },
    )
    assert "[BLOCKED]" in str(out)


@pytest.mark.asyncio
async def test_install_package_happy(monkeypatch):
    monkeypatch.setattr(wt, "_design_block_or_text", lambda *a, **k: None)
    monkeypatch.setattr(wt, "_gate_block_or_text", lambda *a, **k: None)
    monkeypatch.setattr(wt, "session_gate", MagicMock())

    class _Inv:
        def invoke(self, payload):
            assert payload["project_dir"] == "/p"
            assert payload["package_id"] == "Pkg"
            return "[OK] installed"

    monkeypatch.setattr(wt, "_install_package", _Inv())
    out = await call_workflow_tool(
        "uipath_workflow_install_package",
        {"project_dir": "/p", "package_id": "Pkg", "version": "1.0"},
    )
    assert "[OK]" in str(out)


@pytest.mark.asyncio
async def test_validate_delegates(monkeypatch):
    class _Inv:
        def invoke(self, payload):
            return json.dumps({"ok": True, **payload})

    monkeypatch.setattr(wt, "_validate_file", _Inv())
    out = await call_workflow_tool(
        "uipath_workflow_validate",
        {"project_dir": "/p", "file_path": "Main.xaml"},
    )
    data = json.loads(str(out))
    assert data["project_dir"] == "/p"


@pytest.mark.asyncio
async def test_validate_loop_delegates(monkeypatch):
    class _Inv:
        def invoke(self, payload):
            return "loop-done"

    monkeypatch.setattr(wt, "_validate_and_fix_loop", _Inv())
    out = await call_workflow_tool(
        "uipath_workflow_validate_loop",
        {
            "project_dir": "/p",
            "file_path": "Main.xaml",
            "max_attempts": 2,
        },
    )
    assert out == "loop-done"


@pytest.mark.asyncio
async def test_build_and_verify_marks_verified_on_pass(monkeypatch, tmp_path):
    msg = (
        "[OK] build\n"
        "BUILD+VERIFY verdict=pass success=true\n"
    )

    class _Inv:
        def invoke(self, payload):
            return msg

    monkeypatch.setattr(wt, "_build_and_verify_workflow", _Inv())
    monkeypatch.setattr(wt, "session_gate", MagicMock())
    out = await call_workflow_tool(
        "uipath_workflow_build_and_verify",
        {"project_dir": str(tmp_path), "run_after_validate": False},
    )
    assert "[OK]" in str(out)
    wt._maybe_mark_verified_after_build(str(tmp_path), msg)


@pytest.mark.asyncio
async def test_environment_probe_delegates(monkeypatch):
    class _Inv:
        def invoke(self, payload):
            return json.dumps({"probe": True, "project_dir": payload.get("project_dir")})

    monkeypatch.setattr(wt, "_environment_probe", _Inv())
    out = await call_workflow_tool(
        "uipath_workflow_environment_probe", {"project_dir": "/x"}
    )
    assert "probe" in str(out)


@pytest.mark.asyncio
async def test_create_project_delegates(monkeypatch):
    class _Inv:
        def invoke(self, payload):
            return json.dumps({"created": payload["project_name"]})

    monkeypatch.setattr(wt, "_create_project", _Inv())
    out = await call_workflow_tool(
        "uipath_workflow_create_project",
        {
            "project_dir": "/root",
            "project_name": "NewProc",
            "project_type": "process",
            "auto_verify": False,
        },
    )
    assert "NewProc" in str(out)


@pytest.mark.asyncio
async def test_run_blocked_by_gate(monkeypatch):
    monkeypatch.setattr(
        wt,
        "_gate_block_or_text",
        lambda *a, **k: "[BLOCKED] gate",
    )
    out = await call_workflow_tool(
        "uipath_workflow_run",
        {"project_dir": "/p", "file_path": "Main.xaml"},
    )
    assert "[BLOCKED]" in str(out)


@pytest.mark.asyncio
async def test_run_happy(monkeypatch):
    monkeypatch.setattr(wt, "_gate_block_or_text", lambda *a, **k: None)

    class _Inv:
        def invoke(self, payload):
            return "ran"

    monkeypatch.setattr(wt, "_run_workflow", _Inv())
    out = await call_workflow_tool(
        "uipath_workflow_run",
        {"project_dir": "/p", "file_path": "Main.xaml", "verbose": True},
    )
    assert out == "ran"


@pytest.mark.asyncio
async def test_debug_happy(monkeypatch):
    monkeypatch.setattr(wt, "_gate_block_or_text", lambda *a, **k: None)

    class _Inv:
        def invoke(self, payload):
            return "debugging"

    monkeypatch.setattr(wt, "_debug_workflow", _Inv())
    out = await call_workflow_tool(
        "uipath_workflow_debug",
        {"project_dir": "/p", "file_path": "Main.xaml"},
    )
    assert out == "debugging"


@pytest.mark.asyncio
async def test_run_command_happy(monkeypatch):
    monkeypatch.setattr(wt, "_gate_block_or_text", lambda *a, **k: None)

    class _Inv:
        def invoke(self, payload):
            return json.dumps(payload)

    monkeypatch.setattr(wt, "_run_uip_command", _Inv())
    out = await call_workflow_tool(
        "uipath_workflow_run_command",
        {"command": "rpa", "args": ["--help"], "project_dir": "/p"},
    )
    data = json.loads(str(out))
    assert data["command"] == "rpa"


@pytest.mark.asyncio
async def test_deploy_json(monkeypatch):
    monkeypatch.setattr(wt, "_gate_block_or_text", lambda *a, **k: None)

    def fake_deploy(**kwargs):
        return {"status": "ok", "path": kwargs.get("project_path")}

    monkeypatch.setattr(wt, "_deploy", fake_deploy)
    out = await call_workflow_tool(
        "uipath_workflow_deploy",
        {
            "project_path": "/proj",
            "orchestrator_url": "https://orch/",
            "tenant_name": "t",
        },
    )
    data = json.loads(str(out))
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_publish_json(monkeypatch):
    monkeypatch.setattr(wt, "_gate_block_or_text", lambda *a, **k: None)

    def fake_publish(**kwargs):
        return {"published": True, "dir": kwargs.get("project_dir")}

    monkeypatch.setattr(wt, "_publish_project", fake_publish)
    out = await call_workflow_tool(
        "uipath_workflow_publish",
        {"project_dir": "/proj"},
    )
    data = json.loads(str(out))
    assert data["published"] is True


@pytest.mark.asyncio
async def test_session_status_single_project(monkeypatch, tmp_path):
    monkeypatch.setattr(wt.session_gate, "detect_out_of_band_changes", lambda x: None)
    monkeypatch.setattr(
        wt.session_gate,
        "status",
        lambda pd: MagicMock(
            dirty=False,
            verified=True,
            dirty_files=[],
            last_verify_outcome="pass",
        ),
    )
    monkeypatch.setattr(wt.session_gate, "_normalize", lambda s: s)
    monkeypatch.setattr(wt.session_gate, "_gate_enabled", lambda: True)

    def state_to_dict(state):
        return {
            "dirty": state.dirty,
            "verified": state.verified,
            "dirty_files": state.dirty_files,
            "last_verify_outcome": state.last_verify_outcome,
        }

    monkeypatch.setattr(wt.session_gate, "state_to_dict", state_to_dict)

    out = await call_workflow_tool(
        "uipath_workflow_session_status",
        {"project_dir": str(tmp_path)},
    )
    data = json.loads(str(out))
    assert data["gate_enabled"] is True
    assert "project_dir" in data
