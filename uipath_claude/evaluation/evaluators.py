"""Evaluator functions for different evaluation types."""
from typing import Any

# Weights for composite score (outcome + trajectory); both must pass for overall pass.
_OUTCOME_WEIGHT = 0.6
_TRAJECTORY_WEIGHT = 0.4


def final_response_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate the final response - check if generated project is valid.

    Args:
        inputs: Input question/request
        outputs: Agent's output (generated files, validation status)
        reference_outputs: Expected outputs

    Returns:
        Evaluation result with score and details
    """
    score = 0.0
    details = []

    # Check if expected files were created
    expected_files = reference_outputs.get("expected_files", [])
    actual_files = outputs.get("files_created", [])

    files_created = sum(1 for f in expected_files if f in actual_files)
    if expected_files:
        file_score = files_created / len(expected_files)
        score += file_score * 0.3
        details.append(f"Files: {files_created}/{len(expected_files)} created")

    # Check if expected packages were installed
    expected_packages = reference_outputs.get("expected_packages", [])
    actual_packages = outputs.get("packages_installed", [])

    packages_installed = sum(1 for p in expected_packages if p in actual_packages)
    if expected_packages:
        package_score = packages_installed / len(expected_packages)
        score += package_score * 0.3
        details.append(f"Packages: {packages_installed}/{len(expected_packages)} installed")

    # Check if validation passed
    validation_expected = reference_outputs.get("validation_passes", False)
    validation_actual = outputs.get("validation_passed", False)

    if validation_expected == validation_actual:
        score += 0.4
        details.append(f"Validation: {'passed' if validation_actual else 'failed'} (as expected)")
    else:
        details.append(f"Validation: expected {validation_expected}, got {validation_actual}")

    return {
        "score": score,
        "passed": score >= 0.7,
        "details": details,
    }


def trajectory_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate the trajectory - check if agent took correct tool sequence.

    Args:
        inputs: Input question/request (reserved for future use, e.g. task id)
        outputs: Agent's output with trajectory
        reference_outputs: Expected outputs including trajectory

    Returns:
        Evaluation result with score and details
    """
    del inputs  # Same keyword contract as other evaluators for EvaluationRunner
    expected_trajectory = reference_outputs.get("trajectory", [])
    actual_trajectory = outputs.get("trajectory", [])

    if not expected_trajectory:
        return {"score": 1.0, "passed": True, "details": ["No expected trajectory"]}

    # Check subsequence match
    i = j = 0
    matched = 0

    while i < len(expected_trajectory) and j < len(actual_trajectory):
        if expected_trajectory[i] == actual_trajectory[j]:
            matched += 1
            i += 1
        j += 1

    score = matched / len(expected_trajectory)

    details = [
        f"Matched {matched}/{len(expected_trajectory)} expected steps",
        f"Expected: {' -> '.join(expected_trajectory)}",
        f"Actual: {' -> '.join(actual_trajectory[:10])}{'...' if len(actual_trajectory) > 10 else ''}",
    ]

    return {
        "score": score,
        "passed": score >= 0.8,
        "details": details,
    }


def agent_benchmark_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    """
    Single composite evaluation: outcome (artifacts/validation) + trajectory (tools).

    Aggregation:
        - ``score`` = 0.6 * outcome_score + 0.4 * trajectory_score
        - ``passed`` = outcome.passed AND trajectory.passed

    Per-dimension results are under ``dimensions`` for dashboards and debugging.
    """
    outcome = final_response_evaluator(inputs, outputs, reference_outputs)
    trajectory = trajectory_evaluator(inputs, outputs, reference_outputs)
    o_score = float(outcome["score"])
    t_score = float(trajectory["score"])
    composite = _OUTCOME_WEIGHT * o_score + _TRAJECTORY_WEIGHT * t_score
    passed = bool(outcome["passed"]) and bool(trajectory["passed"])
    return {
        "score": composite,
        "passed": passed,
        "details": [
            f"Composite: {composite:.3f} ({_OUTCOME_WEIGHT:.0%} outcome + {_TRAJECTORY_WEIGHT:.0%} trajectory)",
        ],
        "dimensions": {
            "outcome": {
                "score": outcome["score"],
                "passed": outcome["passed"],
                "details": outcome["details"],
            },
            "trajectory": {
                "score": trajectory["score"],
                "passed": trajectory["passed"],
                "details": trajectory["details"],
            },
        },
    }


def single_step_evaluator(
    step_name: str,
    step_args: dict[str, Any],
    step_result: str,
    expected_step: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate a single step - check if tool call was correct.

    Args:
        step_name: Name of the tool called
        step_args: Arguments passed to the tool
        step_result: Result from the tool
        expected_step: Expected step details

    Returns:
        Evaluation result with score and details
    """
    score = 0.0
    details = []

    # Check if correct tool was called
    expected_name = expected_step.get("name", "")
    if step_name == expected_name:
        score += 0.5
        details.append(f"Correct tool: {step_name}")
    else:
        details.append(f"Wrong tool: expected {expected_name}, got {step_name}")
        return {"score": 0.0, "passed": False, "details": details}

    # Check if expected args were provided
    expected_args = expected_step.get("args", {})
    for key, value in expected_args.items():
        if key in step_args and step_args[key] == value:
            score += 0.3 / len(expected_args)
            details.append(f"Correct arg: {key}={value}")
        else:
            details.append(f"Missing/wrong arg: {key}")

    # Check if result indicates success
    expected_success = expected_step.get("success", True)
    actual_success = "error" not in step_result.lower() and "failed" not in step_result.lower()

    if expected_success == actual_success:
        score += 0.2
        details.append(f"Result: {'success' if actual_success else 'failure'} (as expected)")
    else:
        details.append(
            f"Result: expected {'success' if expected_success else 'failure'}, "
            f"got {'success' if actual_success else 'failure'}"
        )

    return {
        "score": score,
        "passed": score >= 0.7,
        "details": details,
    }
