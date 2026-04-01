"""QA validation node for checking generated artifacts."""

import json
from langchain_core.messages import AIMessage
from agent.state import ProjectState


def _validate_artifacts(artifacts: dict[str, str]) -> list[str]:
    """
    Validate generated artifacts against HARD_CONSTRAINTS.

    Checks:
    1. project.json exists and has correct targetFramework
    2. C# only - no VB.Net syntax
    3. Modern activities only - no Classic references
    4. Windows target only
    """
    errors = []

    # Check project.json exists
    if "project.json" not in artifacts:
        errors.append("MISSING: project.json not found in artifacts")
    else:
        try:
            proj = json.loads(artifacts["project.json"])

            # Check target framework
            if proj.get("targetFramework") != "Windows":
                errors.append(
                    f"CONSTRAINT_VIOLATION: targetFramework is "
                    f"'{proj.get('targetFramework')}', must be 'Windows'"
                )

            # Check expression language
            if proj.get("expressionLanguage") != "CSharp":
                errors.append(
                    f"CONSTRAINT_VIOLATION: expressionLanguage is "
                    f"'{proj.get('expressionLanguage')}', must be 'CSharp'"
                )

        except json.JSONDecodeError:
            errors.append("INVALID: project.json is not valid JSON")

    # Check all .cs files for constraint violations
    vb_keywords = ["Dim ", "As String", "AndAlso", "OrElse", "Sub ", "End Sub"]
    classic_namespaces = ["UiPath.Classic.", "UiPath.UIAutomation.Activities.Legacy"]
    console_writes = ["Console.Write(", "Console.WriteLine("]

    for filename, content in artifacts.items():
        if not filename.endswith(".cs"):
            continue

        for keyword in vb_keywords:
            if keyword in content:
                errors.append(
                    f"CONSTRAINT_VIOLATION: VB.Net keyword '{keyword}' found in {filename}"
                )

        for ns in classic_namespaces:
            if ns in content:
                errors.append(
                    f"CONSTRAINT_VIOLATION: Classic namespace '{ns}' found in {filename}"
                )

        for cw in console_writes:
            if cw in content:
                errors.append(
                    f"CONSTRAINT_VIOLATION: Console.Write found in {filename} "
                    f"(use LogMessage instead)"
                )

    # Check at least one entry point exists
    cs_files = [f for f in artifacts if f.endswith(".cs")]
    if not cs_files:
        errors.append("MISSING: No .cs files found in artifacts")

    return errors


async def qa_node(state: ProjectState) -> dict:
    """
    QA validation node: checks artifacts against HARD_CONSTRAINTS.

    Returns validation_errors (empty list if all checks pass).
    Tracks qa_iterations to prevent infinite fix loops.
    """
    artifacts = state.get("artifacts", {})
    qa_iterations = state.get("qa_iterations", 0) + 1

    if not artifacts:
        return {
            "messages": [AIMessage(content="QA: No artifacts to validate.")],
            "validation_errors": ["No artifacts generated"],
            "qa_iterations": qa_iterations,
            "current_phase": "qa",
        }

    errors = _validate_artifacts(artifacts)

    if errors:
        error_report = "\n".join([f"  - {e}" for e in errors])
        summary = f"QA FAILED (iteration {qa_iterations}):\n{error_report}"
    else:
        summary = (
            f"QA PASSED (iteration {qa_iterations}): "
            f"All {len(artifacts)} artifacts validated successfully."
        )

    return {
        "messages": [AIMessage(content=summary)],
        "validation_errors": errors,
        "qa_iterations": qa_iterations,
        "current_phase": "qa",
        "qa_report": {
            "iteration": qa_iterations,
            "total_artifacts": len(artifacts),
            "errors_found": len(errors),
            "errors": errors,
            "passed": len(errors) == 0,
        },
    }
