"""Unit tests for the /pdd lifecycle orchestrator."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from uipath_claude.query import pdd_lifecycle


def _scaffold_ok(parent_dir, project_name):
    project_dir = parent_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project.json").write_text("{}", encoding="utf-8")
    return {"status": "ok", "project_dir": str(project_dir)}


def _scaffold_ok_maestro(parent_dir, project_name):
    sol = parent_dir / f"{project_name}Solution"
    proj = sol / project_name
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "main.flow").write_text("{}", encoding="utf-8")
    return {
        "status": "ok",
        "project_dir": str(proj),
        "solution_dir": str(sol),
    }


@pytest.mark.asyncio
async def test_pdd_lifecycle_invokes_all_stages_in_order(tmp_path):
    """With deploy=True every stage is exercised in the documented order."""
    engine = MagicMock()
    call_order: list[str] = []

    async def llm_side(_engine, _prompt, _user):
        call_order.append("llm")
        return "validated design artifact content"

    publish_fn = MagicMock(return_value={"status": "ok", "package_url": "pkg://x"})
    deploy_fn = MagicMock(return_value={"status": "ok", "process_key": "PROC-1"})

    def fake_scaffold(parent_dir, name):
        call_order.append("scaffold")
        return _scaffold_ok(parent_dir, name)

    def fake_validate(project_dir):
        call_order.append("validate")
        return {"status": "ok", "result": "ok"}

    def fake_run(project_dir):
        call_order.append("run")
        return {"status": "ok", "result": "ok"}

    def wrapped_publish(**kwargs):
        call_order.append("publish")
        return publish_fn(**kwargs)

    def wrapped_deploy(**kwargs):
        call_order.append("deploy")
        return deploy_fn(**kwargs)

    with patch.object(pdd_lifecycle, "invoke_agent_llm", side_effect=llm_side), \
         patch.object(pdd_lifecycle, "_scaffold_process", side_effect=fake_scaffold), \
         patch.object(pdd_lifecycle, "_validate_process", side_effect=fake_validate), \
         patch.object(pdd_lifecycle, "_run_process", side_effect=fake_run):
        result = await pdd_lifecycle.run_pdd_lifecycle(
            "build invoice processor",
            project_type="process",
            deploy=True,
            folder="Shared",
            engine=engine,
            output_root=tmp_path,
            publish_fn=wrapped_publish,
            deploy_fn=wrapped_deploy,
        )

    assert result["status"] == "ok", result
    expected_order = ["llm", "llm", "llm", "llm", "scaffold", "llm", "validate", "run", "publish", "deploy"]
    assert call_order == expected_order
    publish_fn.assert_called_once()
    deploy_fn.assert_called_once()
    paths = result["paths"]
    assert paths["pdd"].endswith("-pdd.md")
    assert paths["sdd"].endswith("-sdd.md")
    assert paths["add"].endswith("-add.md")
    assert paths["tdd"].endswith("-tdd.md")
    assert "project_dir" in paths


@pytest.mark.asyncio
async def test_pdd_lifecycle_short_circuits_on_validate_failure(tmp_path):
    engine = MagicMock()
    publish_fn = MagicMock()
    deploy_fn = MagicMock()

    async def llm_side(*_a, **_kw):
        return "validated design artifact content"

    with patch.object(pdd_lifecycle, "invoke_agent_llm", side_effect=llm_side), \
         patch.object(pdd_lifecycle, "_scaffold_process", side_effect=_scaffold_ok), \
         patch.object(
             pdd_lifecycle,
             "_validate_process",
             return_value={"status": "failed", "error": "[ERROR] validate boom"},
         ), \
         patch.object(pdd_lifecycle, "_run_process") as run_p:
        result = await pdd_lifecycle.run_pdd_lifecycle(
            "x",
            project_type="process",
            deploy=True,
            engine=engine,
            output_root=tmp_path,
            publish_fn=publish_fn,
            deploy_fn=deploy_fn,
        )

    assert result["status"] == "failed"
    assert result["failed_at"] == "validate"
    run_p.assert_not_called()
    publish_fn.assert_not_called()
    deploy_fn.assert_not_called()


@pytest.mark.asyncio
async def test_pdd_lifecycle_skips_publish_deploy_when_no_deploy(tmp_path):
    engine = MagicMock()
    publish_fn = MagicMock()
    deploy_fn = MagicMock()

    async def llm_side(*_a, **_kw):
        return "validated design artifact content"

    with patch.object(pdd_lifecycle, "invoke_agent_llm", side_effect=llm_side), \
         patch.object(pdd_lifecycle, "_scaffold_process", side_effect=_scaffold_ok), \
         patch.object(pdd_lifecycle, "_validate_process", return_value={"status": "ok", "result": "ok"}), \
         patch.object(
             pdd_lifecycle,
             "_run_process",
             return_value={"status": "ok", "result": "ok"},
         ) as run_p:
        result = await pdd_lifecycle.run_pdd_lifecycle(
            "x",
            project_type="process",
            deploy=False,
            engine=engine,
            output_root=tmp_path,
            publish_fn=publish_fn,
            deploy_fn=deploy_fn,
        )

    assert result["status"] == "ok"
    stages = result["stages"]
    assert stages["publish"]["status"] == "skipped"
    assert stages["deploy"]["status"] == "skipped"
    assert stages["run"]["status"] == "ok"
    run_p.assert_called_once()
    publish_fn.assert_not_called()
    deploy_fn.assert_not_called()


@pytest.mark.asyncio
async def test_pdd_lifecycle_routes_maestro_to_flow_commands(tmp_path):
    engine = MagicMock()

    async def llm_side(*_a, **_kw):
        return "validated design artifact content"

    seen: dict[str, bool] = {}

    def fake_scaffold_maestro(parent_dir, name):
        seen["maestro_scaffold"] = True
        return _scaffold_ok_maestro(parent_dir, name)

    def fake_validate_maestro(project_dir):
        seen["maestro_validate"] = True
        return {"status": "ok", "result": "ok"}

    with patch.object(pdd_lifecycle, "invoke_agent_llm", side_effect=llm_side), \
         patch.object(pdd_lifecycle, "_scaffold_maestro", side_effect=fake_scaffold_maestro), \
         patch.object(pdd_lifecycle, "_validate_maestro", side_effect=fake_validate_maestro), \
         patch.object(pdd_lifecycle, "_scaffold_process") as scp, \
         patch.object(pdd_lifecycle, "_validate_process") as vap:
        result = await pdd_lifecycle.run_pdd_lifecycle(
            "x",
            project_type="maestro",
            deploy=False,
            engine=engine,
            output_root=tmp_path,
        )

    assert result["status"] == "ok"
    assert seen == {"maestro_scaffold": True, "maestro_validate": True}
    scp.assert_not_called()
    vap.assert_not_called()


@pytest.mark.asyncio
async def test_pdd_lifecycle_blocks_invalid_design_artifact_before_scaffold(tmp_path):
    engine = MagicMock()

    async def llm_side(*_a, **_kw):
        return "TBD"

    with patch.object(pdd_lifecycle, "invoke_agent_llm", side_effect=llm_side), \
         patch.object(pdd_lifecycle, "_scaffold_process") as scp:
        result = await pdd_lifecycle.run_pdd_lifecycle(
            "x",
            project_type="process",
            deploy=False,
            engine=engine,
            output_root=tmp_path,
        )

    assert result["status"] == "failed"
    assert result["failed_at"] == "pdd"
    scp.assert_not_called()
