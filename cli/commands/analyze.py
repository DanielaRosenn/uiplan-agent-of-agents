"""Analyze command for UiPath Workflow Analyzer."""

import subprocess
from pathlib import Path

from cli.commands import register_command


@register_command(
    name="analyze",
    description="Run UiPath Workflow Analyzer on current project",
    aliases=["wa"],
)
def analyze_command(args: str, context: dict) -> str:
    """Run UiPath Workflow Analyzer on the current project."""
    project_path = context.get("project_path")

    if not project_path:
        return "No UiPath project detected. Navigate to a UiPath project folder."

    project_path = Path(project_path)
    project_json = project_path / "project.json"

    if not project_json.exists():
        return f"project.json not found in {project_path}"

    try:
        result = subprocess.run(
            ["uipath", "studio", "package", "analyze", str(project_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if not output:
                return "Analysis complete. No issues found."
            return f"Analysis Results:\n\n{output}"
        else:
            error = result.stderr.strip() or result.stdout.strip()
            return f"Analysis failed:\n{error}"

    except FileNotFoundError:
        return "UiPath CLI not found. Install with: pip install uipath"
    except subprocess.TimeoutExpired:
        return "Analysis timed out after 120 seconds."
    except Exception as e:
        return f"Error running analyzer: {e}"
