"""Benchmark workflow checks using real UiPath CLI commands."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from uipath_claude.tools.uipath.cli_runner import _find_uip_cli


def _parse_json_from_stdout(stdout: str) -> dict:
    start = stdout.find("{")
    if start < 0:
        raise AssertionError(f"No JSON payload in stdout: {stdout}")
    decoder = json.JSONDecoder()
    payload, _ = decoder.raw_decode(stdout[start:])
    return payload


def _run_uip(command: list[str], cwd: Path, timeout: int = 120) -> dict:
    resolved_command = [_find_uip_cli(), *command]
    proc = subprocess.run(
        resolved_command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"Command failed ({proc.returncode}): {' '.join(resolved_command)}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    combined_output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    return _parse_json_from_stdout(combined_output)


def _benchmark_enabled() -> bool:
    return os.environ.get("UIPATH_RUN_BENCHMARKS", "0").lower() in {"1", "true", "yes"}


@pytest.mark.integration
def test_benchmark_dispatcher_template_get_errors():
    if not _benchmark_enabled():
        pytest.skip("Set UIPATH_RUN_BENCHMARKS=1 to run real UiPath benchmark tests.")

    repo_root = Path(__file__).resolve().parents[2]
    project_dir = repo_root / "templates" / "dispatcher"
    result = _run_uip(
        ["rpa", "get-errors", "--project-dir", str(project_dir), "--output", "json"],
        cwd=repo_root,
    )
    assert result["Result"] == "Success"
    assert result["Data"]["message"] == "No diagnostics found."


@pytest.mark.integration
def test_benchmark_long_running_template_get_errors():
    if not _benchmark_enabled():
        pytest.skip("Set UIPATH_RUN_BENCHMARKS=1 to run real UiPath benchmark tests.")

    repo_root = Path(__file__).resolve().parents[2]
    project_dir = repo_root / "templates" / "long-running"
    result = _run_uip(
        ["rpa", "get-errors", "--project-dir", str(project_dir), "--output", "json"],
        cwd=repo_root,
    )
    assert result["Result"] == "Success"
    assert result["Data"]["message"] == "No diagnostics found."


@pytest.mark.integration
def test_benchmark_maestro_flow_init_and_validate(tmp_path):
    if not _benchmark_enabled():
        pytest.skip("Set UIPATH_RUN_BENCHMARKS=1 to run real UiPath benchmark tests.")

    workspace = tmp_path / "maestro-benchmark"
    workspace.mkdir(parents=True)
    solution_dir = workspace / "BenchmarkFlow"

    _run_uip(["solution", "new", "BenchmarkFlow", "--output", "json"], cwd=workspace)
    _run_uip(["flow", "init", "BenchmarkFlowFlow"], cwd=solution_dir)

    flow_file = solution_dir / "BenchmarkFlowFlow" / "BenchmarkFlowFlow.flow"
    assert flow_file.exists(), f"Expected flow file at {flow_file}"

    result = _run_uip(["flow", "validate", str(flow_file), "--output", "json"], cwd=workspace)
    assert result["Result"] == "Success"
