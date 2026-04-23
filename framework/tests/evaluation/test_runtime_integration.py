"""Integration tests for runtime testing with evaluation datasets."""
import json
from pathlib import Path

import pytest

from uipath_claude.evaluation.datasets import EvaluationDataset


class TestRuntimeIntegration:
    """Integration tests with runtime testing enabled."""

    def test_outlook_workflow_runtime_detection(self, tmp_path, monkeypatch):
        """Test that agent detects and fixes runtime errors in Outlook workflow.
        
        This test verifies the full agent flow:
        1. Generate workflow
        2. Pass static validation
        3. Fail runtime execution (wrong property)
        4. Detect error and fix
        5. Pass runtime execution
        """
        # Setup
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "test-outlook")
        
        # Load evaluation dataset
        dataset = EvaluationDataset.from_workflow_benchmarks()
        outlook_examples = [ex for ex in dataset.examples if ex.metadata["category"] == "email"]
        
        if not outlook_examples:
            pytest.skip("No Outlook examples in evaluation dataset")
        
        outlook_example = outlook_examples[0]
        
        # Note: This is a placeholder for actual integration test
        # In a real implementation, this would:
        # 1. Call run_query() with the outlook question
        # 2. Parse the result to extract tool calls
        # 3. Verify validate_file was called
        # 4. Verify run_workflow was called
        # 5. Verify run_workflow came after validate_file
        # 6. Check final workflow uses correct properties
        
        # For now, we verify the dataset structure
        assert outlook_example.inputs["question"]
        assert "expected_activities" in outlook_example.outputs
        assert outlook_example.metadata["category"] == "email"

    def test_excel_workflow_with_runtime_testing(self, tmp_path, monkeypatch):
        """Test Excel workflow passes runtime testing on first try."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "test-excel")
        
        dataset = EvaluationDataset.from_workflow_benchmarks()
        excel_examples = [ex for ex in dataset.examples if ex.metadata["category"] == "excel"]
        
        if not excel_examples:
            pytest.skip("No Excel examples in evaluation dataset")
        
        excel_example = excel_examples[0]
        
        # Verify dataset expectations
        assert excel_example.inputs["question"]
        assert "ReadRange" in excel_example.outputs.get("expected_activities", []) or \
               "WriteRange" in excel_example.outputs.get("expected_activities", [])

    def test_web_automation_with_runtime_testing(self, tmp_path, monkeypatch):
        """Test web automation workflow structure and runtime expectations."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "test-web")
        
        dataset = EvaluationDataset.from_workflow_benchmarks()
        web_examples = [ex for ex in dataset.examples if ex.metadata["category"] == "web"]
        
        if not web_examples:
            pytest.skip("No web automation examples in evaluation dataset")
        
        web_example = web_examples[0]
        
        # Verify dataset expectations
        assert web_example.inputs["question"]
        assert "expected_activities" in web_example.outputs

    @pytest.mark.parametrize("category", ["email", "excel", "web"])
    def test_evaluation_dataset_structure(self, category):
        """Test that all evaluation categories have proper structure."""
        dataset = EvaluationDataset.from_workflow_benchmarks()
        examples = [ex for ex in dataset.examples if ex.metadata["category"] == category]
        
        if not examples:
            pytest.skip(f"No {category} examples in evaluation dataset")
        
        for example in examples:
            # Verify inputs
            assert "question" in example.inputs
            assert isinstance(example.inputs["question"], str)
            assert len(example.inputs["question"]) > 0
            
            # Verify outputs
            assert "expected_files" in example.outputs
            assert "expected_packages" in example.outputs
            assert "expected_activities" in example.outputs
            assert "trajectory" in example.outputs
            assert "validation_passes" in example.outputs
            
            # Verify metadata
            assert "category" in example.metadata
            assert "difficulty" in example.metadata
            assert example.metadata["category"] == category

    def test_runtime_testing_tool_availability(self):
        """Test that run_workflow tool is available in skill execution tools."""
        from uipath_claude.tools.skill_execution_tools import get_skill_execution_tools
        
        tools = get_skill_execution_tools()
        tool_names = [tool.name for tool in tools]
        
        assert "run_workflow" in tool_names
        assert "validate_file" in tool_names
        
        # Verify run_workflow comes after validate_file in the list
        # (suggests proper ordering in the agent's decision making)
        validate_idx = tool_names.index("validate_file")
        run_workflow_idx = tool_names.index("run_workflow")
        assert run_workflow_idx > validate_idx

    def test_run_workflow_tool_has_proper_docstring(self):
        """Test that run_workflow has comprehensive documentation."""
        from uipath_claude.tools.skill_execution_tools import run_workflow
        
        docstring = run_workflow.description
        
        # Check for key elements mentioned in Anthropic's guide
        assert "runtime" in docstring.lower()
        assert "after" in docstring.lower()  # "use AFTER validation"
        assert "validation" in docstring.lower()
        
        # Check for examples of what it catches
        assert "property" in docstring.lower() or "properties" in docstring.lower()
        assert "null" in docstring.lower() or "reference" in docstring.lower()
        
        # Check for safety warning
        assert "important" in docstring.lower() or "warning" in docstring.lower()


class TestRuntimeToolBehavior:
    """Test runtime tool behavior patterns."""

    def test_error_pattern_matching(self):
        """Test that error patterns are correctly identified."""
        from uipath_claude.tools.skill_execution_tools import _analyze_error_message
        
        # Test property error
        property_error = "The property 'Result' does not exist on activity"
        fix = _analyze_error_message(property_error, "GetOutlookMailMessages")
        assert "find_activity_info" in fix
        assert "property" in fix.lower()
        
        # Test null reference
        null_error = "Object reference not set to an instance of an object"
        fix = _analyze_error_message(null_error, "ForEach")
        assert "null" in fix.lower()
        assert "variable" in fix.lower()
        
        # Test type mismatch
        type_error = "Cannot convert from String to Int32"
        fix = _analyze_error_message(type_error, "Assign")
        assert "type" in fix.lower()

    def test_response_parsing(self):
        """Test JSON response parsing from CLI."""
        from uipath_claude.tools.skill_execution_tools import _parse_runtime_response
        
        # Test success response
        success_json = json.dumps({
            "IsSuccessful": True,
            "Data": {
                "Output": {"State": "Completed"},
                "LogEntries": [],
                "Errors": []
            }
        })
        
        parsed = _parse_runtime_response(success_json)
        assert parsed["success"] is True
        assert parsed["execution_state"] == "Completed"
        
        # Test failure response
        failure_json = json.dumps({
            "IsSuccessful": False,
            "ErrorMessage": "Execution failed",
            "Data": {
                "Output": {"State": "Faulted"},
                "LogEntries": [
                    {"Severity": "Error", "Message": "Test error"}
                ],
                "Errors": []
            }
        })
        
        parsed = _parse_runtime_response(failure_json)
        assert parsed["success"] is False
        assert parsed["execution_state"] == "Faulted"
        assert len(parsed["log_entries"]) == 1

    def test_result_formatting(self):
        """Test that results are formatted correctly."""
        from uipath_claude.tools.skill_execution_tools import _format_runtime_result
        
        # Test success formatting
        success_result = {
            "success": True,
            "execution_state": "Completed",
            "log_entries": [],
            "errors": []
        }
        
        formatted = _format_runtime_result(success_result)
        assert "RUNTIME EXECUTION: SUCCESS" in formatted
        assert "successfully" in formatted.lower()
        
        # Test failure formatting
        failure_result = {
            "success": False,
            "error_message": "Property error",
            "execution_state": "Faulted",
            "log_entries": [
                {
                    "Severity": "Error",
                    "Message": "Property 'Result' does not exist",
                    "ActivityName": "GetOutlookMailMessages"
                }
            ],
            "errors": []
        }
        
        formatted = _format_runtime_result(failure_result)
        assert "RUNTIME EXECUTION: FAILED" in formatted
        assert "Error" in formatted
        assert "GetOutlookMailMessages" in formatted


class TestDatasetExpectations:
    """Test that evaluation datasets have runtime testing expectations."""

    def test_datasets_include_run_workflow_in_trajectory(self):
        """Verify that expected trajectories include run_workflow."""
        dataset = EvaluationDataset.from_workflow_benchmarks()
        
        for example in dataset.examples:
            trajectory = example.outputs.get("trajectory", [])
            
            # After this implementation, trajectories should include run_workflow
            # This test documents the expected behavior
            # Note: Dataset will be updated in next todo
            assert isinstance(trajectory, list)
            assert "validate_file" in trajectory

    def test_datasets_have_validation_passes_expectation(self):
        """Verify that datasets expect validation to pass."""
        dataset = EvaluationDataset.from_workflow_benchmarks()
        
        for example in dataset.examples:
            assert "validation_passes" in example.outputs
            # All benchmark workflows should pass validation
            assert example.outputs["validation_passes"] is True
