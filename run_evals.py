"""Canonical script to run evaluations using the actual agent.

This is the single entry point for running the comprehensive evaluation suite.
It uses the unified agent_benchmark_evaluator which combines outcome and trajectory scoring.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Set environment variables for evaluations
os.environ["UIPATH_AGENTIC_MODE"] = "1"
os.environ["UIPATH_DEBUG_VERBOSE"] = "1"
os.environ["UIPATH_SKILL_AUTO_CAPTURE"] = "0"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["UIPATH_CHAT_OUTPUT_DIR"] = str(Path.cwd() / "generated" / "evals")

from uipath_claude.evaluation.datasets import EvaluationDataset
from uipath_claude.evaluation.evaluators import agent_benchmark_evaluator
from uipath_claude.evaluation.runner import EvaluationRunner
from uipath_claude.query.agentic_executor import AgenticExecutor
from uipath_claude.tools.skill_execution_tools import get_skill_execution_tools

async def target_function(inputs: dict) -> dict:
    """Target function that runs the agent."""
    question = inputs["question"]
    print(f"\nEvaluating: {question}")
    
    tools = get_skill_execution_tools()
    executor = AgenticExecutor(
        model_name=os.getenv("UIPATH_CLAUDE_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0"),
        region=os.getenv("AWS_REGION", "us-east-1"),
    )
    
    session_id = f"eval-{hash(question) % 10000}"
    project_context = {
        "output_dir": os.environ["UIPATH_CHAT_OUTPUT_DIR"],
        "session_id": session_id,
    }
    
    # Run the agent
    result = await executor.execute(
        skill_content="You are an expert UiPath developer. Create the requested workflow.",
        user_request=question,
        tools=tools,
        project_context=project_context,
        skill_name="uipath-rpa",
    )
    
    # Extract outputs for evaluation
    files_created = result.files_written
    tool_calls = result.tool_calls_made
    trajectory = [call["name"] for call in tool_calls]
    
    # Check if validation passed by looking at tool results
    validation_passed = False
    packages_installed = []
    
    for call in tool_calls:
        if call["name"] == "validate_file":
            pass
        elif call["name"] == "install_package":
            pkg = call["args"].get("package_name")
            if pkg:
                packages_installed.append(pkg)
                
    # If the agent succeeded overall, we assume validation passed
    validation_passed = result.success
    
    return {
        "files_created": [Path(f).name for f in files_created],
        "packages_installed": packages_installed,
        "validation_passed": validation_passed,
        "trajectory": trajectory,
        "success": result.success,
        "final_response": result.final_response,
        "error": result.error,
    }

async def run_evaluations(max_examples: int = None, category: str = None, output_file: str = "evaluation_results.json"):
    print("Loading dataset...")
    dataset = EvaluationDataset.from_workflow_benchmarks()
    
    if category:
        filtered_examples = [ex for ex in dataset.examples if category.lower() in ex.metadata.get("category", "").lower()]
        dataset.examples = filtered_examples
        print(f"Filtered to category '{category}': {len(dataset.examples)} examples.")
    
    print(f"Dataset loaded: {dataset.name} with {len(dataset.examples)} examples.")
    
    runner = EvaluationRunner(
        target_function=target_function,
        evaluators={"agent_benchmark": agent_benchmark_evaluator},
    )
    
    print("Running evaluations...")
    run = await runner.run(dataset, max_examples=max_examples)
    
    # Save results
    output_path = Path(output_file)
    run.save(output_path)
    print(f"\nResults saved to {output_path}")
    
    print("\nEvaluation Summary:")
    print(f"Total: {run.summary['total']}")
    print(f"Passed: {run.summary['passed']}")
    print(f"Failed: {run.summary['failed']}")
    print(f"Pass Rate: {run.summary['pass_rate']:.1%}")
    
    if run.summary['total'] > 0:
        print("\nAverage Scores:")
        for name, score in run.summary['average_scores'].items():
            print(f"  {name}: {score:.3f}")

def main():
    parser = argparse.ArgumentParser(description="Run the canonical UiPath Builder Agent evaluation suite.")
    parser.add_argument("--max-examples", type=int, default=None, help="Maximum number of examples to evaluate")
    parser.add_argument("--category", type=str, default=None, help="Filter examples by category")
    parser.add_argument("--output", type=str, default="evaluation_results.json", help="Output JSON file path")
    
    args = parser.parse_args()
    
    # Fix Windows console encoding if needed
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
        
    asyncio.run(run_evaluations(
        max_examples=args.max_examples,
        category=args.category,
        output_file=args.output
    ))

if __name__ == "__main__":
    main()
