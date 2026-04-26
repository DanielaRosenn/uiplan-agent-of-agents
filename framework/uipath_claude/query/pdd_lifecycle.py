"""Full PDD lifecycle: PDD -> SDD -> ADD -> TDD -> scaffold -> implement -> validate -> run -> publish -> deploy.

This is the orchestrator behind the ``/pdd`` slash command. It composes the
existing agent prompts (``BAAgent`` / ``SAAgent`` / ``ADDAgent`` / ``TDDAgent``
/ ``DeveloperAgent`` / ``QAAgent``) with the workflow tools that scaffold,
validate, run, publish, and deploy a UiPath project.

Each stage short-circuits on failure: the result dictionary always contains
``status="ok"|"failed"`` plus, when failed, ``failed_at=<stage>`` and
``error=<message>``. Tests assert call order via mock side-effects.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from uipath_claude.agents.add import ADDAgent
from uipath_claude.agents.ba import BAAgent
from uipath_claude.agents.developer import DeveloperAgent
from uipath_claude.agents.qa import QAAgent
from uipath_claude.agents.sa import SAAgent
from uipath_claude.agents.tdd import TDDAgent
from uipath_claude.artifacts.writer import BootstrapArtifactWriter
from uipath_claude.query.agent_invoke import invoke_agent_llm
from uipath_claude.query.conversation import ConversationEngine
from uipath_claude.query.engine_factory import create_conversation_engine_from_env
from uipath_claude.tools import skill_execution_tools as set_mod
from uipath_claude.tools import deploy_tool

STAGES = (
    "pdd",
    "sdd",
    "add",
    "tdd",
    "scaffold",
    "implement",
    "validate",
    "run",
    "publish",
    "deploy",
)


def _ok(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": "ok", **(payload or {})}


def _fail(stage: str, message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": "failed", "failed_at": stage, "error": message, **(payload or {})}


def _is_error_payload(text: str) -> bool:
    if not isinstance(text, str):
        return False
    t = text.strip()
    return t.startswith("[ERROR]") or t.startswith("[BLOCKED]") or t.startswith("[FAIL]")


async def run_pdd_lifecycle(
    user_request: str,
    *,
    project_type: str = "process",
    deploy: bool = False,
    folder: str = "Personal Workspace",
    engine: ConversationEngine | None = None,
    output_root: Path | None = None,
    process_name: str | None = None,
    publish_fn: Callable[..., dict[str, Any]] | None = None,
    deploy_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Drive the full PDD-to-deploy lifecycle.

    Args:
        user_request: Natural-language request that seeds the PDD.
        project_type: ``process`` (default, RPA) or ``maestro`` (Flow).
        deploy: When True, also pack/publish/create-process on Orchestrator.
        folder: Orchestrator folder for the create-process step.
        engine: Optional conversation engine (defaults to env-based).
        output_root: Where to write docs/<stage>/<stamp>.md and the project.
        process_name: Override for the Orchestrator process display name.
        publish_fn / deploy_fn: Test seams; default to the modernized
            wrappers in ``uipath_claude.tools.deploy_tool``.

    Returns:
        ``{"status": "ok"|"failed", "failed_at"?: str, "error"?: str,
            "stages": {<stage>: <stage payload>}, "paths": {...}}``
    """
    eng = engine or create_conversation_engine_from_env()
    root = Path(output_root) if output_root is not None else Path.cwd()
    writer = BootstrapArtifactWriter(root)
    stages: dict[str, dict[str, Any]] = {}
    paths: dict[str, str] = {}

    try:
        ba = BAAgent()
        pdd = await invoke_agent_llm(eng, ba.get_system_prompt(), user_request)
        design_error = _validate_design_artifact("pdd", pdd)
        if design_error:
            return _fail("pdd", design_error, {"stages": stages, "paths": paths})
        pdd_path = writer.write_pdd(pdd)
        paths["pdd"] = str(pdd_path)
        stages["pdd"] = _ok({"length": len(pdd or "")})
    except Exception as exc:
        return _fail("pdd", str(exc), {"stages": stages, "paths": paths})

    try:
        sa = SAAgent()
        sdd = await invoke_agent_llm(
            eng, sa.get_system_prompt(), f"Create SDD based on this PDD:\n\n{pdd}"
        )
        design_error = _validate_design_artifact("sdd", sdd)
        if design_error:
            return _fail("sdd", design_error, {"stages": stages, "paths": paths})
        sdd_path = writer.write_sdd(sdd)
        paths["sdd"] = str(sdd_path)
        stages["sdd"] = _ok({"length": len(sdd or "")})
    except Exception as exc:
        return _fail("sdd", str(exc), {"stages": stages, "paths": paths})

    try:
        add_agent = ADDAgent()
        add_doc = await invoke_agent_llm(
            eng,
            add_agent.get_system_prompt(),
            f"Create ADD based on this SDD:\n\n{sdd}",
        )
        design_error = _validate_design_artifact("add", add_doc)
        if design_error:
            return _fail("add", design_error, {"stages": stages, "paths": paths})
        add_path = writer.write_add(add_doc)
        paths["add"] = str(add_path)
        stages["add"] = _ok({"length": len(add_doc or "")})
    except Exception as exc:
        return _fail("add", str(exc), {"stages": stages, "paths": paths})

    try:
        tdd_agent = TDDAgent()
        tdd_doc = await invoke_agent_llm(
            eng,
            tdd_agent.get_system_prompt(),
            f"Create TDD based on this ADD:\n\n{add_doc}",
        )
        design_error = _validate_design_artifact("tdd", tdd_doc)
        if design_error:
            return _fail("tdd", design_error, {"stages": stages, "paths": paths})
        tdd_path = writer.write_tdd(tdd_doc)
        paths["tdd"] = str(tdd_path)
        stages["tdd"] = _ok({"length": len(tdd_doc or "")})
    except Exception as exc:
        return _fail("tdd", str(exc), {"stages": stages, "paths": paths})

    project_name = (process_name or _slug_from_request(user_request))[:64]
    parent_dir = root / "generated" / "automation" / writer.stamp
    parent_dir.mkdir(parents=True, exist_ok=True)

    if project_type == "maestro":
        scaffold_result = _scaffold_maestro(parent_dir, project_name)
    else:
        scaffold_result = _scaffold_process(parent_dir, project_name)

    if scaffold_result.get("status") == "failed":
        stages["scaffold"] = scaffold_result
        return _fail("scaffold", scaffold_result.get("error", ""), {"stages": stages, "paths": paths})
    project_dir = scaffold_result["project_dir"]
    paths["project_dir"] = project_dir
    stages["scaffold"] = scaffold_result

    try:
        dev = DeveloperAgent()
        impl = await invoke_agent_llm(
            eng,
            dev.get_system_prompt(),
            (
                "Implement based on:\n\nPDD:\n"
                f"{pdd}\n\nSDD:\n{sdd}\n\nADD:\n{add_doc}\n\nTDD:\n{tdd_doc}\n\n"
                "Produce an implementation plan and any code/XAML deltas needed "
                "for the existing scaffold at the project_dir below.\n"
                f"project_dir: {project_dir}"
            ),
        )
        impl_path = Path(project_dir) / "IMPLEMENTATION_PLAN.md"
        impl_path.write_text(impl or "", encoding="utf-8")
        paths["implementation_plan"] = str(impl_path)
        stages["implement"] = _ok({"length": len(impl or "")})
    except Exception as exc:
        return _fail("implement", str(exc), {"stages": stages, "paths": paths})

    if project_type == "maestro":
        validate_result = _validate_maestro(project_dir)
    else:
        validate_result = _validate_process(project_dir)
    stages["validate"] = validate_result
    if validate_result.get("status") == "failed":
        return _fail("validate", validate_result.get("error", ""), {"stages": stages, "paths": paths})

    if project_type == "maestro":
        run_result = _run_maestro(project_dir)
    else:
        run_result = _run_process(project_dir)
    stages["run"] = run_result
    if run_result.get("status") == "failed":
        return _fail("run", run_result.get("error", ""), {"stages": stages, "paths": paths})

    if not deploy:
        stages["publish"] = {"status": "skipped", "reason": "deploy=False"}
        stages["deploy"] = {"status": "skipped", "reason": "deploy=False"}
        try:
            qa = QAAgent()
            qa_doc = await invoke_agent_llm(
                eng,
                qa.get_system_prompt(),
                f"Validate this implementation plan and scaffold:\n\n{impl}",
            )
            qa_path = writer.write_qa(qa_doc)
            paths["qa"] = str(qa_path)
        except Exception:
            pass
        return {"status": "ok", "stages": stages, "paths": paths}

    publish = publish_fn or deploy_tool.publish_project
    try:
        publish_payload = publish(project_dir=project_dir, project_type=project_type)
        stages["publish"] = publish_payload
        if publish_payload.get("status") == "failed":
            return _fail("publish", publish_payload.get("error", ""), {"stages": stages, "paths": paths})
    except Exception as exc:
        return _fail("publish", str(exc), {"stages": stages, "paths": paths})

    deploy_call = deploy_fn or deploy_tool.deploy_to_orchestrator_v2
    try:
        deploy_payload = deploy_call(
            project_dir=project_dir,
            project_type=project_type,
            folder=folder,
            process_name=project_name,
            publish_payload=publish_payload,
        )
        stages["deploy"] = deploy_payload
        if deploy_payload.get("status") == "failed":
            return _fail("deploy", deploy_payload.get("error", ""), {"stages": stages, "paths": paths})
    except Exception as exc:
        return _fail("deploy", str(exc), {"stages": stages, "paths": paths})

    return {"status": "ok", "stages": stages, "paths": paths}


def _slug_from_request(text: str) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "", (text or "").title())
    return s or "GeneratedProcess"


def _validate_design_artifact(stage: str, text: str | None) -> str | None:
    """Reject empty/error/placeholder design artifacts before downstream stages."""
    body = (text or "").strip()
    if len(body) < 20:
        return f"{stage.upper()} artifact is too short to validate ({len(body)} chars)"
    lowered = body.lower()
    placeholders = ("todo", "tbd", "lorem ipsum", "[insert", "<insert")
    if _is_error_payload(body) or any(marker in lowered for marker in placeholders):
        return f"{stage.upper()} artifact contains an error marker or unresolved placeholder"
    return None


def _scaffold_process(parent_dir: Path, project_name: str) -> dict[str, Any]:
    result_text = set_mod.create_project.invoke(
        {
            "project_dir": str(parent_dir),
            "project_name": project_name,
            "project_type": "process",
            "auto_verify": False,
        }
    )
    if _is_error_payload(result_text):
        return {"status": "failed", "error": result_text[:400]}
    project_dir = str((parent_dir / project_name).resolve())
    return {"status": "ok", "project_dir": project_dir, "cli_output": result_text[:400]}


def _scaffold_maestro(parent_dir: Path, project_name: str) -> dict[str, Any]:
    uip = shutil.which("uip") or "uip"
    solution_name = f"{project_name}Solution"
    sol_dir = parent_dir / solution_name
    try:
        proc1 = subprocess.run(
            [uip, "solution", "new", solution_name, "--output", "json"],
            cwd=str(parent_dir),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc1.returncode != 0:
            return {"status": "failed", "error": f"uip solution new: {proc1.stderr or proc1.stdout}"[:400]}

        proc2 = subprocess.run(
            [uip, "flow", "init", project_name, "--output", "json"],
            cwd=str(sol_dir),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc2.returncode != 0:
            return {"status": "failed", "error": f"uip flow init: {proc2.stderr or proc2.stdout}"[:400]}

        proc3 = subprocess.run(
            [
                uip,
                "solution",
                "project",
                "add",
                str(sol_dir / project_name),
                str(sol_dir / f"{solution_name}.uipx"),
                "--output",
                "json",
            ],
            cwd=str(parent_dir),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc3.returncode != 0:
            return {"status": "failed", "error": f"uip solution project add: {proc3.stderr or proc3.stdout}"[:400]}
    except FileNotFoundError:
        return {"status": "failed", "error": "uip CLI not found on PATH"}
    except subprocess.TimeoutExpired as exc:
        return {"status": "failed", "error": f"timeout in maestro scaffold: {exc}"}

    return {
        "status": "ok",
        "project_dir": str((sol_dir / project_name).resolve()),
        "solution_dir": str(sol_dir.resolve()),
    }


def _validate_process(project_dir: str) -> dict[str, Any]:
    text = set_mod.build_and_verify_workflow.invoke(
        {
            "project_dir": project_dir,
            "run_after_validate": False,
            "require_studio_debug": False,
            "max_attempts": 2,
            "auto_install_packages": False,
        }
    )
    if _is_error_payload(text):
        return {"status": "failed", "error": text[:400]}
    return {"status": "ok", "result": text[:400]}


def _validate_maestro(project_dir: str) -> dict[str, Any]:
    uip = shutil.which("uip") or "uip"
    flow = next(Path(project_dir).glob("*.flow"), None)
    if flow is None:
        return {"status": "failed", "error": f"no .flow file in {project_dir}"}
    proc = subprocess.run(
        [uip, "flow", "validate", str(flow), "--output", "json"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return {"status": "failed", "error": out[:400]}
    return {"status": "ok", "result": out[:400]}


def _run_process(project_dir: str) -> dict[str, Any]:
    text = set_mod.build_and_verify_workflow.invoke(
        {
            "project_dir": project_dir,
            "run_after_validate": True,
            "require_studio_debug": False,
            "max_attempts": 1,
            "auto_install_packages": False,
        }
    )
    if _is_error_payload(text):
        return {"status": "failed", "error": text[:400]}
    return {"status": "ok", "result": text[:400]}


def _run_maestro(project_dir: str) -> dict[str, Any]:
    return {"status": "skipped", "reason": "uip flow debug requires cloud auth; covered by integration tests"}
