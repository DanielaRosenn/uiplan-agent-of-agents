"""
Tool for deploying UiPath workflows to Orchestrator/Studio Web
"""
import subprocess
import json
from pathlib import Path
from typing import Optional, Literal


def deploy_to_orchestrator(
    project_path: str,
    orchestrator_url: str,
    tenant_name: str,
    folder_path: str = "Shared",
    account_name: Optional[str] = None,
    process_name: Optional[str] = None,
    create_process: bool = True,
    environment: Optional[str] = None
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
        folder_path: Folder path in Orchestrator (default: "Shared")
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
            folder_path="Shared",
            process_name="MyProcess"
        )
    """
    project_path = Path(project_path).resolve()
    
    if not (project_path / "project.json").exists():
        return {
            "success": False,
            "error": f"project.json not found in {project_path}"
        }
    
    # Read project.json for metadata
    with open(project_path / "project.json", "r", encoding="utf-8") as f:
        project_config = json.load(f)
    
    project_name = project_config.get("name", project_path.name)
    project_version = project_config.get("projectVersion", "1.0.0")
    
    if not process_name:
        process_name = project_name
    
    result = {
        "success": False,
        "project_name": project_name,
        "project_version": project_version,
        "steps": []
    }
    
    try:
        # Step 1: Pack the project
        result["steps"].append("Packing project...")
        pack_output = project_path / f"{project_name}.{project_version}.nupkg"
        
        pack_cmd = [
            "uipath", "package", "pack",
            str(project_path),
            "-o", str(pack_output),
            "--outputType", "Process"
        ]
        
        pack_result = subprocess.run(
            pack_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if pack_result.returncode != 0:
            result["error"] = f"Pack failed: {pack_result.stderr}"
            result["steps"].append(f"❌ Pack failed: {pack_result.stderr[:200]}")
            return result
        
        result["steps"].append(f"✅ Packed: {pack_output.name}")
        result["package_path"] = str(pack_output)
        
        # Step 2: Deploy to Orchestrator
        result["steps"].append("Deploying to Orchestrator...")
        
        deploy_cmd = [
            "uipath", "package", "deploy",
            str(pack_output),
            orchestrator_url,
            tenant_name,
            "--folder", folder_path
        ]
        
        if account_name:
            deploy_cmd.extend(["--accountName", account_name])
        
        deploy_result = subprocess.run(
            deploy_cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if deploy_result.returncode != 0:
            result["error"] = f"Deploy failed: {deploy_result.stderr}"
            result["steps"].append(f"❌ Deploy failed: {deploy_result.stderr[:200]}")
            return result
        
        result["steps"].append("✅ Deployed to Orchestrator")
        result["deployed"] = True
        
        # Step 3: Create/Update Process (optional)
        if create_process:
            result["steps"].append("Creating/updating process...")
            
            # Note: Process creation typically requires additional Orchestrator API calls
            # This is a placeholder for the full implementation
            result["steps"].append(f"⚠️  Process '{process_name}' - manual creation may be needed")
            result["process_name"] = process_name
            result["message"] = "Package deployed. Create process in Orchestrator UI if needed."
        
        result["success"] = True
        result["orchestrator_url"] = orchestrator_url
        result["tenant"] = tenant_name
        result["folder"] = folder_path
        
        return result
        
    except FileNotFoundError:
        return {
            "success": False,
            "error": "UiPath CLI not found. Install from https://docs.uipath.com/automation-cloud/automation-cloud/latest/admin-guide/managing-automation-suite-using-the-cli",
            "steps": ["❌ UiPath CLI not installed"]
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Deployment timed out",
            "steps": result["steps"] + ["❌ Operation timed out"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "steps": result["steps"] + [f"❌ Error: {str(e)}"]
        }


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
        folder_path=folder_name
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
  $env:UIPATH_FOLDER_PATH = "Shared"  # Optional
  $env:UIPATH_API_KEY = "your-api-key"  # Optional, for authentication
"""
        }
    
    config["orchestrator_url"] = orchestrator_url
    config["tenant_name"] = tenant_name
    config["folder_path"] = os.getenv("UIPATH_FOLDER_PATH", "Shared")
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
                "description": "Folder path in Orchestrator (default: Shared)",
                "default": "Shared"
            },
            "process_name": {
                "type": "string",
                "description": "Name for the process (optional, defaults to project name)"
            }
        },
        "required": ["project_path"]
    }
}
