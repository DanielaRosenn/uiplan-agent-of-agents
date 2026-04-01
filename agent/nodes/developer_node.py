"""Developer node for generating UiPath project files."""

import json
from langchain_core.messages import AIMessage
from agent.state import ProjectState


def _generate_project_json(sdd: dict) -> str:
    """Generate a minimal valid UiPath project.json from the SDD."""
    project_name = sdd.get("project_name", "MyProject")
    namespace = sdd.get("namespace", f"Company.{project_name}")

    project = {
        "name": project_name,
        "projectId": "00000000-0000-0000-0000-000000000000",
        "description": f"Auto-generated UiPath project: {project_name}",
        "main": "Main.cs",
        "dependencies": {
            pkg: "[24.10.0]" for pkg in sdd.get("nuget_packages", [
                "UiPath.System.Activities",
                "UiPath.UIAutomation.Activities",
            ])
        },
        "toolVersion": "24.10.0",
        "projectVersion": "1.0.0",
        "schemaVersion": "24.10.0",
        "studioVersion": "24.10.0",
        "designOptions": {
            "projectProfile": "Developement",
            "outputType": "Process",
        },
        "targetFramework": "Windows",
        "expressionLanguage": "CSharp",
        "entryPoints": [
            {
                "filePath": "Main.cs",
                "uniqueId": "00000000-0000-0000-0000-000000000001",
                "input": [],
                "output": [],
            }
        ],
        "runtimeOptions": {
            "autoDispose": False,
            "netFrameworkLazyLoading": False,
            "isPausable": True,
            "requiresUserInteraction": True,
            "supportsPersistence": False,
        },
    }

    return json.dumps(project, indent=2)


def _generate_main_cs(sdd: dict) -> str:
    """Generate a placeholder Main.cs coded workflow."""
    project_name = sdd.get("project_name", "MyProject")
    namespace = sdd.get("namespace", f"Company.{project_name}")

    activities = sdd.get("coded_activities", [])
    activity_calls = ""
    for act in activities:
        class_name = act.get("class_name", "UnknownActivity")
        activity_calls += f"""
        // {act.get('purpose', '')}
        // TODO: Implement {class_name}
        Log(LogLevel.Info, "Executing {class_name}...");
"""

    return f"""using System;
using System.Collections.Generic;
using UiPath.CodedWorkflows;
using UiPath.Core.Activities;

namespace {namespace}
{{
    /// <summary>
    /// Main entry point for {project_name}.
    /// Auto-generated - customize as needed.
    /// </summary>
    public class Main : CodedWorkflow
    {{
        [Workflow]
        public void Execute()
        {{
            Log(LogLevel.Info, "Starting {project_name}...");
            {activity_calls}
            Log(LogLevel.Info, "{project_name} completed successfully.");
        }}
    }}
}}
"""


def _generate_activity_cs(activity: dict, namespace: str) -> str:
    """Generate a coded activity .cs file."""
    class_name = activity.get("class_name", "UnknownActivity")
    purpose = activity.get("purpose", "")
    inputs = activity.get("inputs", [])
    outputs = activity.get("outputs", [])

    input_params = ", ".join([f"string {inp}" for inp in inputs]) if inputs else ""
    output_type = "string" if outputs else "void"

    return_statement = ""
    if outputs:
        return_statement = f'            return "TODO: implement {class_name}";'

    return f"""using System;
using UiPath.CodedWorkflows;
using UiPath.Core.Activities;

namespace {namespace}
{{
    /// <summary>
    /// {purpose}
    /// </summary>
    public class {class_name} : CodedWorkflow
    {{
        [Workflow]
        public {output_type} Execute({input_params})
        {{
            Log(LogLevel.Info, "Executing {class_name}...");

            // TODO: Implement {purpose}
{return_statement}

            Log(LogLevel.Info, "{class_name} completed.");
        }}
    }}
}}
"""


async def developer_node(state: ProjectState) -> dict:
    """
    Developer node: generates UiPath project files from SDD.

    Produces:
    - project.json
    - Main.cs (entry point)
    - One .cs file per coded_activity in the SDD
    """
    sdd = state.get("sdd", {})
    project_name = sdd.get("project_name", state.get("project_name", "MyProject"))
    namespace = sdd.get("namespace", f"Company.{project_name}")

    artifacts = {}

    # Generate project.json
    artifacts["project.json"] = _generate_project_json(sdd)

    # Generate Main.cs
    artifacts["Main.cs"] = _generate_main_cs(sdd)

    # Generate coded activity files
    for activity in sdd.get("coded_activities", []):
        class_name = activity.get("class_name", "UnknownActivity")
        filename = f"{class_name}.cs"
        artifacts[filename] = _generate_activity_cs(activity, namespace)

    file_list = "\n".join([f"  - {f}" for f in artifacts.keys()])
    summary = f"Generated {len(artifacts)} files for {project_name}:\n{file_list}"

    return {
        "messages": [AIMessage(content=summary)],
        "artifacts": artifacts,
        "current_phase": "generation",
    }
