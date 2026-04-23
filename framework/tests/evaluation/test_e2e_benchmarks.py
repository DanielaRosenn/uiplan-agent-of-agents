"""End-to-end benchmark tests for UiPath workflow generation."""
import pytest

from uipath_claude.evaluation.datasets import EvaluationDataset
from uipath_claude.evaluation.evaluators import (
    agent_benchmark_evaluator,
    final_response_evaluator,
    trajectory_evaluator,
)
from uipath_claude.evaluation.runner import EvaluationRunner


@pytest.fixture
def workflow_dataset():
    """Create workflow benchmark dataset."""
    return EvaluationDataset.from_workflow_benchmarks()


@pytest.fixture
def evaluators():
    """Canonical single composite evaluator for benchmark runs."""
    return {"agent_benchmark": agent_benchmark_evaluator}


def test_dataset_creation(workflow_dataset):
    """Test that dataset is created correctly."""
    assert workflow_dataset.name == "UiPath Workflow Benchmarks"
    assert len(workflow_dataset.examples) >= 3
    assert all(ex.inputs and ex.outputs for ex in workflow_dataset.examples)


def test_dataset_save_load(workflow_dataset, tmp_path):
    """Test dataset save and load."""
    path = tmp_path / "dataset.json"
    workflow_dataset.save(path)

    loaded = EvaluationDataset.load(path)
    assert loaded.name == workflow_dataset.name
    assert len(loaded.examples) == len(workflow_dataset.examples)


def test_final_response_evaluator():
    """Test final response evaluator."""
    inputs = {"question": "Create workflow"}
    outputs = {
        "files_created": ["Main.xaml", "project.json"],
        "packages_installed": ["UiPath.Mail.Activities"],
        "validation_passed": True,
    }
    reference = {
        "expected_files": ["Main.xaml", "project.json"],
        "expected_packages": ["UiPath.Mail.Activities"],
        "validation_passes": True,
    }

    result = final_response_evaluator(inputs, outputs, reference)
    assert result["score"] == 1.0
    assert result["passed"] is True


def test_trajectory_evaluator():
    """Test trajectory evaluator (runner-compatible signature)."""
    inputs = {"question": "Create workflow"}
    outputs = {
        "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file"],
    }
    reference = {
        "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file"],
    }

    result = trajectory_evaluator(inputs, outputs, reference)
    assert result["score"] == 1.0
    assert result["passed"] is True


def test_trajectory_evaluator_partial_match():
    """Out-of-order extra steps: only a subsequence of expected tools is matched."""
    inputs = {"question": "Create workflow"}
    outputs = {
        "trajectory": ["ensure_project_structure", "write_file", "install_package", "validate_file"],
    }
    reference = {
        "trajectory": ["ensure_project_structure", "install_package", "write_file"],
    }

    result = trajectory_evaluator(inputs, outputs, reference)
    # Matched ensure -> install -> write in order within actual, but write appears after install is delayed
    assert result["score"] == pytest.approx(2 / 3)
    assert result["passed"] is False  # below 0.8 threshold


def test_agent_benchmark_evaluator_dimensions():
    """Composite bundles outcome and trajectory with top-level score/passed."""
    inputs = {"question": "Create workflow"}
    outputs = {
        "files_created": ["Main.xaml", "project.json"],
        "packages_installed": ["UiPath.Mail.Activities"],
        "validation_passed": True,
        "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file"],
    }
    reference = {
        "expected_files": ["Main.xaml", "project.json"],
        "expected_packages": ["UiPath.Mail.Activities"],
        "validation_passes": True,
        "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file"],
    }
    result = agent_benchmark_evaluator(inputs, outputs, reference)
    assert "dimensions" in result
    assert "outcome" in result["dimensions"]
    assert "trajectory" in result["dimensions"]
    assert result["dimensions"]["outcome"]["passed"] is True
    assert result["dimensions"]["trajectory"]["passed"] is True
    assert result["passed"] is True
    assert 0.0 <= result["score"] <= 1.0


@pytest.mark.asyncio
async def test_evaluation_runner(workflow_dataset, evaluators):
    """Test evaluation runner with composite evaluator (keyword call path)."""
    # Mock target function
    async def mock_target(inputs):
        return {
            "files_created": ["Main.xaml", "project.json"],
            "packages_installed": ["UiPath.Mail.Activities"],
            "validation_passed": True,
            "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file"],
        }

    runner = EvaluationRunner(mock_target, evaluators)
    run = await runner.run(workflow_dataset, max_examples=1)

    assert run.dataset_name == "UiPath Workflow Benchmarks"
    assert len(run.results) == 1
    assert run.summary["total"] == 1
    scores = run.results[0].scores
    assert "agent_benchmark" in scores
    assert "dimensions" in scores["agent_benchmark"]
    assert "outcome" in scores["agent_benchmark"]["dimensions"]
    assert "trajectory" in scores["agent_benchmark"]["dimensions"]


@pytest.mark.asyncio
async def test_evaluation_runner_with_failure(workflow_dataset, evaluators):
    """Test evaluation runner with failed example."""
    # Mock target function that fails
    async def mock_target(inputs):
        raise ValueError("Test error")

    runner = EvaluationRunner(mock_target, evaluators)
    run = await runner.run(workflow_dataset, max_examples=1)

    assert len(run.results) == 1
    assert run.results[0].passed is False
    assert run.results[0].error is not None
