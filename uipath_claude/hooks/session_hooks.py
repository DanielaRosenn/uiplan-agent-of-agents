"""Session hooks from UiPath/skills repo."""
import json
import subprocess
import os
from pathlib import Path
from typing import Optional


def get_skills_hooks_path() -> Optional[Path]:
    """Get the path to the skills repo hooks folder."""
    # Find the repo root
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            hooks_path = current / "skills" / "hooks"
            if hooks_path.exists():
                return hooks_path
        current = current.parent
    return None


def load_skills_hooks() -> dict:
    """Load hooks configuration from skills repo."""
    hooks_path = get_skills_hooks_path()
    if not hooks_path:
        return {}
    
    hooks_file = hooks_path / "hooks.json"
    if not hooks_file.exists():
        return {}
    
    try:
        return json.loads(hooks_file.read_text())
    except Exception:
        return {}


def run_session_start_hooks(verbose: bool = False) -> list[dict]:
    """
    Run SessionStart hooks from the skills repo.
    
    Returns:
        List of results with status and output for each hook
    """
    results = []
    hooks_config = load_skills_hooks()
    hooks_path = get_skills_hooks_path()
    
    if not hooks_path:
        return results
    
    session_hooks = hooks_config.get("hooks", {}).get("SessionStart", [])
    
    for hook_group in session_hooks:
        for hook in hook_group.get("hooks", []):
            if hook.get("type") != "command":
                continue
            
            command = hook.get("command", "")
            timeout = hook.get("timeout", 60)
            status_msg = hook.get("statusMessage", "Running hook...")
            
            # Replace ${CLAUDE_PLUGIN_ROOT} with actual path
            command = command.replace("${CLAUDE_PLUGIN_ROOT}", str(hooks_path.parent))
            
            if verbose:
                print(f"  {status_msg}")
            
            result = {
                "command": command,
                "status": "success",
                "output": "",
            }
            
            try:
                # Run the hook
                proc = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(hooks_path.parent),
                    env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(hooks_path.parent)},
                )
                result["output"] = proc.stdout or proc.stderr
                if proc.returncode != 0:
                    result["status"] = "failed"
                    result["error"] = proc.stderr
            except subprocess.TimeoutExpired:
                result["status"] = "timeout"
                result["error"] = f"Hook timed out after {timeout}s"
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
            
            results.append(result)
    
    return results


def check_uip_installed() -> tuple[bool, str]:
    """Check if uip CLI is installed and accessible."""
    try:
        result = subprocess.run(
            ["uip", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"uip CLI installed: {version}"
        return False, "uip CLI not responding"
    except FileNotFoundError:
        return False, "uip CLI not found. Run: npm install -g @uipath/cli"
    except Exception as e:
        return False, f"Error checking uip: {e}"
