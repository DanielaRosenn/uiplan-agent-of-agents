"""End-to-end benchmark tests for UiPath workflow generation."""
import pytest
from pathlib import Path

from uipath_claude.evaluation.datasets import EvaluationDataset
from uipath_claude.evaluation.evaluators import (
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
    """Create evaluator dict."""
    return {
        "final_response": final_response_evaluator,
        "trajectory": trajectory_evaluator,
    }


def test_dataset_creation(workflow_dataset):
    """Test that dataset is created correctly."""
    assert workflow_dataset.name == "UiPath Workflow Benchmarks"
    assert len(workflow_dataset.examples) == 3
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
    """Test trajectory evaluator."""
    outputs = {
        "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file"],
    }
    reference = {
        "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file"],
    }
    
    result = trajectory_evaluator(outputs, reference)
    assert result["score"] == 1.0
    assert result["passed"] is True


def test_trajectory_evaluator_partial_match():
    """Test trajectory evaluator with partial match."""
    outputs = {
        "trajectory": ["ensure_project_structure", "write_file", "install_package", "validate_file"],
    }
    reference = {
        "trajectory": ["ensure_project_structure", "install_package", "write_file"],
    }
    
    result = trajectory_evaluator(outputs, reference)
    # Should match 3/3 steps (subsequence match)
    assert result["score"] == 1.0
    assert result["passed"] is True


@pytest.mark.asyncio
async def test_evaluation_runner(workflow_dataset, evaluators):
    """Test evaluation runner."""
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
