"""
Tool for deploying UiPath workflows to Orchestrator/Studio Web
"""
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional


def _uip_bin() -> str:
    return shutil.which("uip") or "uip"


def _run_uip(args: list[str], cwd: Optional[str | Path] = None, timeout: int = 600) -> dict[str, Any]:
    """Run a uip CLI command, returning a structured result."""
    cmd = [_uip_bin(), *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )
    except FileNotFoundError:
        return {"status": "failed", "error": "uip CLI not found on PATH", "cmd": cmd}
    except subprocess.TimeoutExpired as exc:
        return {"status": "failed", "error": f"timeout: {exc}", "cmd": cmd}
    payload = {
        "status": "ok" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "cmd": cmd,
    }
    if proc.returncode != 0 and "error" not in payload:
        payload["error"] = (proc.stderr or proc.stdout or "uip command failed")[:400]
    return payload


_NUPKG_PATTERN = re.compile(r"([^\s\"']+\.nupkg)", re.IGNORECASE)


def _folder_policy_error(
    folder_path: Optional[str],
    *,
    human_confirmed: bool = False,
    approved_by: Optional[str] = None,
) -> Optional[str]:
    folder = (folder_path or "").strip()
    if not folder:
        return "folder_path is required; no default Shared folder is allowed"
    lowered = folder.lower()
    if "prod" in lowered or "production" in lowered:
        return "Production targets are blocked from assistant sessions"
    safe = "personal" in lowered or "dev" in lowered
    if safe:
        return None
    if not human_confirmed or not (approved_by or "").strip():
        return (
            f"folder_path={folder!r} requires explicit human approval metadata "
            "(human_confirmed=true and approved_by)"
        )
    return None


def _extract_nupkg(text: str, search_dir: Optional[Path] = None) -> Optional[str]:
    """Best-effort: pull a .nupkg path out of CLI stdout, falling back to a fs scan."""
    for line in (text or "").splitlines():
        match = _NUPKG_PATTERN.search(line)
        if match:
            return match.group(1)
    if search_dir is not None and search_dir.exists():
        nupkgs = sorted(search_dir.rglob("*.nupkg"), key=lambda p: p.stat().st_mtime, reverse=True)
        if nupkgs:
            return str(nupkgs[0])
    return None


def _pack_args_for_project(project_type: str, project_dir: Path, out_dir: Path) -> Optional[list[str]]:
    if project_type == "maestro":
        return ["flow", "pack", str(project_dir), "--output", str(out_dir), "--output-format", "json"]
    if project_type == "process":
        return [
            "solution",
            "pack",
            str(project_dir),
            "--output",
            str(out_dir),
            "--output-format",
            "json",
        ]
    return None


def preflight_project(project_dir: str, project_type: str = "process") -> dict[str, Any]:
    """Run the local restore/analyze gate before pack/publish/deploy."""
    pdir = Path(project_dir).resolve()
    if project_type == "maestro":
        flow = next(pdir.glob("*.flow"), None)
        if flow is None:
            return {"status": "failed", "stage": "preflight", "error": f"no .flow file in {pdir}"}
        validate = _run_uip(["flow", "validate", str(flow), "--output", "json"], cwd=pdir)
        if validate["status"] != "ok":
            return {"status": "failed", "stage": "preflight_validate", "validate": validate, "error": validate.get("error", "flow validate failed")}
        return {"status": "ok", "validate": validate}

    restore = _run_uip(["solution", "restore", str(pdir), "--output-format", "json"], cwd=pdir)
    if restore["status"] != "ok":
        return {"status": "failed", "stage": "preflight_restore", "restore": restore, "error": restore.get("error", "restore failed")}

    analyze = _run_uip(["rpa", "analyze", "--project-path", str(pdir), "--output", "json"], cwd=pdir)
    if analyze["status"] != "ok":
        return {"status": "failed", "stage": "preflight_analyze", "restore": restore, "analyze": analyze, "error": analyze.get("error", "analyze failed")}
    return {"status": "ok", "restore": restore, "analyze": analyze}


def publish_project(
    project_dir: str,
    project_type: str = "process",
    folder_path: Optional[str] = None,
    human_confirmed: bool = False,
    approved_by: Optional[str] = None,
) -> dict[str, Any]:
    """Pack and publish a UiPath project to Orchestrator using the modern ``uip`` CLI.

    For ``project_type="process"`` (default RPA): runs ``uip solution pack`` then
    ``uip solution publish`` to push the resulting ``.nupkg`` to the tenant.

    For ``project_type="maestro"``: runs ``uip flow pack`` then ``uip solution publish``.

    Args:
        project_dir: Absolute path to the project (folder containing ``project.json``
            for ``process``, or the Maestro project folder for ``maestro``).
        project_type: ``process`` or ``maestro``.

    Returns:
        ``{"status": "ok"|"failed", "package_path": str?, "publish": <uip result>}``
    """
    pdir = Path(project_dir).resolve()
    if not pdir.exists():
        return {"status": "failed", "error": f"project dir not found: {pdir}"}

    if folder_path:
        folder_error = _folder_policy_error(
            folder_path, human_confirmed=human_confirmed, approved_by=approved_by
        )
        if folder_error:
            return {"status": "failed", "stage": "policy", "error": folder_error}

    preflight = preflight_project(str(pdir), project_type=project_type)
    if preflight.get("status") != "ok":
        return {"status": "failed", "stage": "preflight", "error": preflight.get("error", "preflight failed"), "preflight": preflight}

    out_dir = pdir.parent / "_packages"
    out_dir.mkdir(parents=True, exist_ok=True)

    pack_args = _pack_args_for_project(project_type, pdir, out_dir)
    if pack_args is None:
        return {
            "status": "failed",
            "stage": "project_type",
            "error": f"unsupported project_type: {project_type}",
        }
    pack = _run_uip(pack_args)

    if pack["status"] != "ok":
        return {"status": "failed", "stage": "pack", "error": pack.get("error", "pack failed"), "pack": pack}

    nupkg = _extract_nupkg(pack.get("stdout", ""), out_dir)
    if not nupkg:
        return {
            "status": "failed",
            "stage": "pack",
            "error": "could not locate .nupkg after pack",
            "pack": pack,
        }

    publish = _run_uip(["solution", "publish", nupkg, "--output-format", "json"])
    if publish["status"] != "ok":
        return {
            "status": "failed",
            "stage": "publish",
            "error": publish.get("error", "publish failed"),
            "package_path": nupkg,
            "pack": pack,
            "publish": publish,
        }

    return {
        "status": "ok",
        "package_path": nupkg,
        "preflight": preflight,
        "pack": pack,
        "publish": publish,
    }


def deploy_to_orchestrator_v2(
    project_dir: str,
    project_type: str = "process",
    folder: str = "",
    process_name: Optional[str] = None,
    publish_payload: Optional[dict[str, Any]] = None,
    environment: Optional[str] = None,
    human_confirmed: bool = False,
    approved_by: Optional[str] = None,
) -> dict[str, Any]:
    """Modern deploy: publish (if needed) then create the Orchestrator process.

    Calls ``publish_project`` first when ``publish_payload`` is not supplied,
    then materializes the process via ``uip or processes create`` (RPA) or
    ``uip flow process create`` (Maestro).

    Args:
        project_dir: Project directory.
        project_type: ``process`` or ``maestro``.
        folder: Orchestrator folder for the new process.
        process_name: Display name for the process (defaults to project folder name).
        publish_payload: Optional pre-computed payload from ``publish_project``;
            avoids re-packing when the orchestrator wants the same artefact reused.
        environment: Optional environment to associate with the process.

    Returns:
        ``{"status": "ok"|"failed", "publish": ..., "create": ...,
            "process_name": ..., "folder": ...}``
    """
    pdir = Path(project_dir).resolve()
    name = process_name or pdir.name
    folder_error = _folder_policy_error(
        folder, human_confirmed=human_confirmed, approved_by=approved_by
    )
    if folder_error:
        return {"status": "failed", "stage": "policy", "error": folder_error}

    publish = publish_payload
    if publish is None:
        publish = publish_project(
            project_dir=str(pdir),
            project_type=project_type,
            folder_path=folder,
            human_confirmed=human_confirmed,
            approved_by=approved_by,
        )
    if publish.get("status") != "ok":
        return {"status": "failed", "stage": "publish", "publish": publish}

    if project_type == "maestro":
        create_args = ["flow", "process", "create", name, "--folder", folder, "--output-format", "json"]
    else:
        create_args = ["or", "processes", "create", name, "--folder", folder, "--output-format", "json"]
    if environment:
        create_args += ["--environment", environment]

    create = _run_uip(create_args)
    if create["status"] != "ok":
        return {
            "status": "failed",
            "stage": "create",
            "publish": publish,
            "create": create,
            "error": create.get("error", "create failed"),
        }

    process_key: Optional[str] = None
    try:
        data = json.loads(create.get("stdout") or "{}")
        process_key = data.get("Key") or data.get("key") or data.get("Id") or data.get("id")
    except Exception:
        process_key = None

    return {
        "status": "ok",
        "publish": publish,
        "create": create,
        "process_name": name,
        "process_key": process_key,
        "folder": folder,
    }



def deploy_to_orchestrator(
    project_path: str,
    orchestrator_url: str = "",
    tenant_name: str = "",
    folder_path: str = "",
    account_name: Optional[str] = None,
    process_name: Optional[str] = None,
    create_process: bool = True,
    environment: Optional[str] = None,
    project_type: str = "process",
    human_confirmed: bool = False,
    approved_by: Optional[str] = None,
) -> dict:
    """
    Deploy a UiPath project to Orchestrator or Studio Web.
    
    This uses the UiPath CLI to:
    1. Pack the project into a .nupkg file
    2. Deploy to Orchestrator
    3. Optionally create/update a process
    
    Args:
        project_path: Path to the UiPath project directory containing project.json
        orchestrator_url: Orchestrator URL (e.g., https://cloud.uipath.com/yourorg/yourservice)
        tenant_name: Tenant name in Orchestrator
        folder_path: Folder path in Orchestrator. Required; no default Shared
            folder is allowed, and Production is blocked.
        account_name: Account name (for authentication, optional if using API key from env)
        process_name: Name for the process (defaults to project name)
        create_process: Whether to create/update process after deployment
        environment: Environment to associate with process (optional)
    
    Returns:
        dict with deployment status, package info, and process details
        
    Example:
        result = deploy_to_orchestrator(
            project_path="./MyProject",
            orchestrator_url="https://cloud.uipath.com/myorg/myservice",
            tenant_name="MyTenant",
            folder_path="Dev",
            process_name="MyProcess"
        )
    """
    pdir = Path(project_path).resolve()
    if project_type != "maestro" and not (pdir / "project.json").exists():
        return {
            "success": False,
            "error": f"project.json not found in {pdir}",
        }

    v2 = deploy_to_orchestrator_v2(
        project_dir=str(pdir),
        project_type=project_type,
        folder=folder_path,
        process_name=process_name,
        environment=environment,
        human_confirmed=human_confirmed,
        approved_by=approved_by,
    )

    legacy = {
        "success": v2.get("status") == "ok",
        "project_name": (process_name or pdir.name),
        "process_name": v2.get("process_name"),
        "process_key": v2.get("process_key"),
        "package_path": (v2.get("publish") or {}).get("package_path"),
        "folder": v2.get("folder", folder_path),
        "tenant": tenant_name,
        "orchestrator_url": orchestrator_url,
        "v2": v2,
    }
    if not legacy["success"]:
        legacy["error"] = v2.get("error") or "deploy failed"
    return legacy


def deploy_to_studio_web(
    project_path: str,
    organization_name: str,
    tenant_name: str,
    folder_name: str = "Personal Workspace"
) -> dict:
    """
    Deploy a UiPath project specifically to Studio Web (cloud workspace).
    
    Args:
        project_path: Path to the UiPath project
        organization_name: UiPath organization name
        tenant_name: Tenant name
        folder_name: Folder/workspace name (default: "Personal Workspace")
    
    Returns:
        dict with deployment status
    """
    # Studio Web uses Automation Cloud URL format
    cloud_url = f"https://cloud.uipath.com/{organization_name}/{tenant_name}"
    
    return deploy_to_orchestrator(
        project_path=project_path,
        orchestrator_url=cloud_url,
        tenant_name=tenant_name,
        folder_path=folder_name,
    )


def get_deployment_config_from_env() -> dict:
    """
    Get deployment configuration from environment variables or config file.
    
    Environment variables:
        UIPATH_ORCHESTRATOR_URL
        UIPATH_TENANT_NAME
        UIPATH_FOLDER_PATH
        UIPATH_ACCOUNT_NAME
        UIPATH_API_KEY
    
    Returns:
        dict with configuration or error
    """
    import os
    
    config = {}
    
    # Check for required environment variables
    orchestrator_url = os.getenv("UIPATH_ORCHESTRATOR_URL")
    tenant_name = os.getenv("UIPATH_TENANT_NAME")
    
    if not orchestrator_url or not tenant_name:
        return {
            "success": False,
            "error": "Missing required environment variables: UIPATH_ORCHESTRATOR_URL and UIPATH_TENANT_NAME",
            "help": """
Set environment variables:
  $env:UIPATH_ORCHESTRATOR_URL = "https://cloud.uipath.com/yourorg/yourservice"
  $env:UIPATH_TENANT_NAME = "YourTenant"
  $env:UIPATH_FOLDER_PATH = "Dev"  # Required for deploy/publish
  $env:UIPATH_API_KEY = "your-api-key"  # Optional, for authentication
"""
        }
    
    config["orchestrator_url"] = orchestrator_url
    config["tenant_name"] = tenant_name
    config["folder_path"] = (
        os.getenv("UIPATH_FOLDER_PATH")
        or os.getenv("UIPATH_DEFAULT_FOLDER")
        or ""
    )
    config["account_name"] = os.getenv("UIPATH_ACCOUNT_NAME")
    config["success"] = True
    
    return config


# Tool descriptor for LangChain
DEPLOY_TOOL_SCHEMA = {
    "name": "deploy_to_orchestrator",
    "description": """Deploy a UiPath workflow project to Orchestrator or Studio Web.
    
This tool packages the project and deploys it to UiPath Orchestrator or Studio Web (cloud).
Requires UiPath CLI to be installed and configured.

Use this when the user wants to:
- Deploy to Orchestrator
- Publish to Studio Web
- Upload to cloud workspace
- Create a process in Maestro

The tool will:
1. Pack the project into a .nupkg file
2. Upload to Orchestrator
3. Report deployment status
""",
    "parameters": {
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Path to the UiPath project directory"
            },
            "orchestrator_url": {
                "type": "string",
                "description": "Orchestrator URL (e.g., https://cloud.uipath.com/orgname/tenantname)"
            },
            "tenant_name": {
                "type": "string",
                "description": "Tenant name in Orchestrator"
            },
            "folder_path": {
                "type": "string",
                "description": "Folder path in Orchestrator. Required; no default Shared folder is allowed."
            },
            "process_name": {
                "type": "string",
                "description": "Name for the process (optional, defaults to project name)"
            }
        },
        "required": ["project_path"]
    }
}
