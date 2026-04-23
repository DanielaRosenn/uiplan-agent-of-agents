"""Evaluation runner for running evaluations on datasets."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
import json

from uipath_claude.evaluation.datasets import EvaluationDataset, Example


@dataclass
class EvaluationResult:
    """Result from a single evaluation."""
    
    example_id: int
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    scores: dict[str, Any]
    passed: bool
    duration_ms: float
    error: str | None = None


@dataclass
class EvaluationRun:
    """Complete evaluation run results."""
    
    dataset_name: str
    timestamp: str
    results: list[EvaluationResult]
    summary: dict[str, Any] = field(default_factory=dict)
    
    def calculate_summary(self) -> None:
        """Calculate summary statistics."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        avg_scores = {}
        for result in self.results:
            for eval_name, eval_result in result.scores.items():
                if eval_name not in avg_scores:
                    avg_scores[eval_name] = []
                avg_scores[eval_name].append(eval_result.get("score", 0.0))
        
        for eval_name in avg_scores:
            avg_scores[eval_name] = sum(avg_scores[eval_name]) / len(avg_scores[eval_name])
        
        self.summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "average_scores": avg_scores,
            "total_duration_ms": sum(r.duration_ms for r in self.results),
        }
    
    def save(self, path: Path) -> None:
        """Save evaluation run to JSON file."""
        data = {
            "dataset_name": self.dataset_name,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "results": [
                {
                    "example_id": r.example_id,
                    "inputs": r.inputs,
                    "outputs": r.outputs,
                    "scores": r.scores,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in self.results
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


class EvaluationRunner:
    """Runner for executing evaluations."""
    
    def __init__(
        self,
        target_function: Callable[[dict], dict],
        evaluators: dict[str, Callable],
    ):
        """
        Initialize evaluation runner.
        
        Args:
            target_function: Function that takes inputs and returns outputs
            evaluators: Dict of evaluator name to evaluator function
        """
        self.target_function = target_function
        self.evaluators = evaluators
    
    async def run(
        self,
        dataset: EvaluationDataset,
        max_examples: int | None = None,
    ) -> EvaluationRun:
        """
        Run evaluation on dataset.
        
        Args:
            dataset: Dataset to evaluate on
            max_examples: Maximum number of examples to evaluate (None for all)
        
        Returns:
            Evaluation run results
        """
        examples = dataset.examples[:max_examples] if max_examples else dataset.examples
        results = []
        
        for i, example in enumerate(examples):
            start_time = datetime.now()
            
            try:
                # Run target function
                outputs = await self.target_function(example.inputs)
                
                # Run evaluators
                scores = {}
                for eval_name, evaluator in self.evaluators.items():
                    scores[eval_name] = evaluator(
                        inputs=example.inputs,
                        outputs=outputs,
                        reference_outputs=example.outputs,
                    )
                
                # Determine if passed (all evaluators must pass)
                passed = all(s.get("passed", False) for s in scores.values())
                error = None
                
            except Exception as e:
                outputs = {}
                scores = {}
                passed = False
                error = str(e)
            
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            results.append(EvaluationResult(
                example_id=i,
                inputs=example.inputs,
                outputs=outputs,
                scores=scores,
                passed=passed,
                duration_ms=duration_ms,
                error=error,
            ))
        
        run = EvaluationRun(
            dataset_name=dataset.name,
            timestamp=datetime.now().isoformat(),
            results=results,
        )
        run.calculate_summary()
        
        return run
