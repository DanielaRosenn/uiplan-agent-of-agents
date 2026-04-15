"""Dataset management for evaluation."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass
class Example:
    """A single evaluation example."""
    
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationDataset:
    """Dataset for evaluation."""
    
    name: str
    examples: list[Example]
    description: str = ""
    
    @classmethod
    def from_workflow_benchmarks(cls) -> "EvaluationDataset":
        """Create dataset from workflow benchmarks.
        
        Includes expectations for both static validation and runtime testing.
        After runtime testing implementation, workflows should:
        1. Pass static validation (validate_file)
        2. Pass runtime execution (run_workflow)
        3. Include both tools in the agent's trajectory
        """
        examples = [
            Example(
                inputs={"question": "Create a UiPath workflow that reads the first 5 emails from Outlook and logs each subject"},
                outputs={
                    "expected_files": ["Main.xaml", "project.json"],
                    "expected_packages": ["UiPath.Mail.Activities"],
                    "expected_activities": ["GetOutlookMailMessages", "LogMessage"],
                    "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file", "run_workflow"],
                    "validation_passes": True,
                    "runtime_passes": True,
                },
                metadata={"category": "email", "difficulty": "medium"},
            ),
            Example(
                inputs={"question": "Create a UiPath workflow that reads data from an Excel file and writes it to another sheet"},
                outputs={
                    "expected_files": ["Main.xaml", "project.json"],
                    "expected_packages": ["UiPath.Excel.Activities"],
                    "expected_activities": ["ReadRange", "WriteRange"],
                    "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file", "run_workflow"],
                    "validation_passes": True,
                    "runtime_passes": True,
                },
                metadata={"category": "excel", "difficulty": "easy"},
            ),
            Example(
                inputs={"question": "Create a UiPath workflow that opens a browser, navigates to google.com and types a search query"},
                outputs={
                    "expected_files": ["Main.xaml", "project.json"],
                    "expected_packages": ["UiPath.UIAutomation.Activities"],
                    "expected_activities": ["OpenBrowser", "TypeInto"],
                    "trajectory": ["ensure_project_structure", "install_package", "write_file", "validate_file", "run_workflow"],
                    "validation_passes": True,
                    "runtime_passes": True,
                },
                metadata={"category": "web", "difficulty": "medium"},
            ),
        ]
        
        return cls(
            name="UiPath Workflow Benchmarks",
            examples=examples,
            description="Benchmark tests for common UiPath workflow generation tasks",
        )
    
    def save(self, path: Path) -> None:
        """Save dataset to JSON file."""
        data = {
            "name": self.name,
            "description": self.description,
            "examples": [
                {
                    "inputs": ex.inputs,
                    "outputs": ex.outputs,
                    "metadata": ex.metadata,
                }
                for ex in self.examples
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "EvaluationDataset":
        """Load dataset from JSON file."""
        with open(path) as f:
            data = json.load(f)
        
        examples = [
            Example(
                inputs=ex["inputs"],
                outputs=ex["outputs"],
                metadata=ex.get("metadata", {}),
            )
            for ex in data["examples"]
        ]
        
        return cls(
            name=data["name"],
            examples=examples,
            description=data.get("description", ""),
        )
