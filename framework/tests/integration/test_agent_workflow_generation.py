"""Integration test for agent workflow generation with validation.

This test simulates the full agent flow:
1. User requests a workflow
2. Agent selects appropriate skill
3. Agent generates workflow
4. Agent validates with uip CLI
5. If errors, agent should fix them
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from uipath_claude.cli.app import (
    _select_relevant_skills,
    _build_runtime_skill_context,
    _tokenize,
)
from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.artifacts.materialize import (
    materialize_from_assistant_text,
    validate_generated_project,
)
from uipath_claude.query.conversation import ConversationEngine


def test_skill_selection_for_outlook_workflow():
    """Test that Outlook email workflow selects uipath-rpa-workflows skill."""
    registry = SkillRegistry()
    skills = registry.load_skills()
    
    prompt = "Create a UiPath workflow that reads emails from Outlook and prints the subject of each email"
    selected = _select_relevant_skills(prompt, skills, max_items=2)
    
    skill_names = [s.get("name") for s in selected]
    print(f"Selected skills for Outlook workflow: {skill_names}")
    
    assert (
        "uipath-rpa" in skill_names
        or "uipath-rpa-workflows" in skill_names
        or "uipath-automation" in skill_names
    ), \
        f"Expected RPA skill, got: {skill_names}"


def test_skill_context_includes_xaml_guidance():
    """Test that runtime context includes XAML generation guidance."""
    registry = SkillRegistry()
    skills = registry.load_skills()
    
    prompt = "Create a UiPath workflow that reads emails from Outlook"
    context = _build_runtime_skill_context(prompt, skills)
    
    assert context, "Runtime context should not be empty"
    assert "XAML" in context or "xaml" in context or "workflow" in context.lower(), \
        "Context should include workflow/XAML guidance"
    print(f"Context length: {len(context)} chars")


async def test_full_workflow_generation_and_validation():
    """Test full workflow generation with LLM and validation."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        print("Skipping LLM test - no AWS credentials")
        return
    
    registry = SkillRegistry()
    skills = registry.load_skills()
    
    prompt = "Create a simple UiPath workflow that logs 'Hello World' to the console"
    
    selected = _select_relevant_skills(prompt, skills, max_items=2)
    context = _build_runtime_skill_context(prompt, skills)
    
    from uipath_claude.config import DEFAULT_BEDROCK_MODEL

    model_name = os.getenv("UIPATH_CLAUDE_MODEL", DEFAULT_BEDROCK_MODEL)
    region = os.getenv("AWS_REGION", "us-east-1")
    
    engine = ConversationEngine(model_name=model_name, region=region)
    
    system_prompt = """You are UiPath Claude Code. Generate UiPath XAML workflows.

When asked to create a workflow, output a complete XAML file using this format:

<<<UIPATH_FILE path="HelloWorld.xaml">>>
...complete XAML content...
<<<END_UIPATH_FILE>>>

Also create a project.json file:

<<<UIPATH_FILE path="project.json">>>
...project configuration...
<<<END_UIPATH_FILE>>>
"""
    
    if context:
        system_prompt += f"\n\nSkill guidance:\n{context[:4000]}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    
    print("Calling LLM to generate workflow...")
    response = await engine.run(messages=messages, tools=[], system_prompt=system_prompt)
    print(f"Response length: {len(response)} chars")
    
    output_dir = Path("generated/test-agent-flow")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    written = materialize_from_assistant_text(
        str(response),
        output_root=output_dir,
        allow_project_files=True,
    )
    
    print(f"Written files: {[str(p) for p in written]}")
    
    if written:
        validation = validate_generated_project(output_dir)
        print(f"Validation success: {validation['success']}")
        if not validation["success"]:
            print(f"Validation errors: {validation['errors'][:3]}")
        
        assert validation["success"], f"Generated workflow should validate: {validation['errors']}"


def main():
    """Run all tests."""
    print("=" * 60)
    print("Test 1: Skill Selection")
    print("=" * 60)
    test_skill_selection_for_outlook_workflow()
    print("PASSED\n")
    
    print("=" * 60)
    print("Test 2: Skill Context")
    print("=" * 60)
    test_skill_context_includes_xaml_guidance()
    print("PASSED\n")
    
    print("=" * 60)
    print("Test 3: Full Workflow Generation (requires AWS)")
    print("=" * 60)
    asyncio.run(test_full_workflow_generation_and_validation())
    print("PASSED\n")
    
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
