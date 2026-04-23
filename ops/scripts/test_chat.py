#!/usr/bin/env python
"""
Interactive test script for the conversational agent.

Usage:
    python ops/scripts/test_chat.py                    # Interactive mode
    python ops/scripts/test_chat.py --prompt "..."     # Single prompt mode
    python ops/scripts/test_chat.py --test-skills      # Test skill selection only
"""
import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_FW = _REPO / "framework"
sys.path.insert(0, str(_FW if (_FW / "uipath_claude").is_dir() else _REPO))


def test_skill_selection(prompt: str):
    """Test skill selection for a given prompt."""
    from uipath_claude.skills.registry import SkillRegistry
    from uipath_claude.cli.app import _select_relevant_skills, _score_skill, _tokenize
    
    print(f"\nPrompt: {prompt}")
    print("-" * 60)
    
    registry = SkillRegistry()
    skills = registry.load_skills()
    
    # Get scores for all skills
    user_tokens = _tokenize(prompt)
    scores = {}
    for skill in skills:
        score = _score_skill(skill, prompt, user_tokens)
        scores[skill["name"]] = score
    
    # Select top skills
    selected_skills = _select_relevant_skills(prompt, skills, max_items=1)
    selected = selected_skills[0]["name"] if selected_skills else None
    
    print(f"Selected skill: {selected}")
    print(f"\nTop scores:")
    for name, score in sorted(scores.items(), key=lambda x: -x[1])[:10]:
        marker = " <--" if name == selected else ""
        print(f"  {name}: {score}{marker}")
    
    return selected, scores


def run_single_prompt(prompt: str, stream: bool = True):
    """Run a single prompt through the agent."""
    import asyncio
    import os
    from uipath_claude.skills.registry import SkillRegistry
    from uipath_claude.query.conversation import ConversationEngine
    from uipath_claude.cli.app import (
        _select_relevant_skills,
        _build_runtime_skill_context,
    )
    from uipath_claude.artifacts.materialize import (
        contains_file_blocks,
        materialize_from_assistant_text,
    )
    
    print(f"\nPrompt: {prompt}")
    print("=" * 60)
    
    # Load skills
    registry = SkillRegistry()
    skills = registry.load_skills()
    
    # Select skill
    selected_skills = _select_relevant_skills(prompt, skills, max_items=1)
    selected_skill = selected_skills[0]["name"] if selected_skills else None
    print(f"Selected skill: {selected_skill}")
    
    # Build context
    skill_context = _build_runtime_skill_context(prompt, skills)
    print(f"Skill context: {len(skill_context)} chars")
    
    # Build system prompt
    system_prompt = """You are UiPath Claude Code. You build UiPath Studio automations.

When creating files, use this format:
<<<UIPATH_FILE path="filename.xaml">>>
...file content...
<<<END_UIPATH_FILE>>>
"""
    if skill_context:
        system_prompt += f"\n\n{skill_context}"
    
    # Create engine
    from uipath_claude.config import DEFAULT_BEDROCK_MODEL

    model_name = os.getenv("UIPATH_CLAUDE_MODEL", DEFAULT_BEDROCK_MODEL)
    region = os.getenv("AWS_REGION", "us-east-1")
    
    print(f"\nModel: {model_name}")
    print(f"Region: {region}")
    print("-" * 60)
    
    engine = ConversationEngine(model_name=model_name, region=region)
    
    # Run conversation (async)
    print("\nAssistant response:")
    print("-" * 60)
    
    messages = [{"role": "user", "content": prompt}]
    
    async def get_response():
        if stream:
            parts = []
            def on_delta(delta):
                print(delta, end="", flush=True)
                parts.append(delta)
            await engine.run_stream(messages, tools=[], system_prompt=system_prompt, on_delta=on_delta)
            return "".join(parts)
        else:
            return await engine.run(messages, tools=[], system_prompt=system_prompt)
    
    response = asyncio.run(get_response())
    print("\n")
    
    # Check for file blocks
    if contains_file_blocks(response):
        print("-" * 60)
        print("File blocks detected in response.")
        
        # Optionally materialize
        output_dir = Path("generated/test-chat")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        written = materialize_from_assistant_text(response, output_dir)
        if written:
            print(f"Files written to {output_dir}:")
            for f in written:
                print(f"  - {f}")
    
    return response


def interactive_mode():
    """Run interactive chat mode."""
    import asyncio
    import os
    from uipath_claude.skills.registry import SkillRegistry
    from uipath_claude.query.conversation import ConversationEngine
    from uipath_claude.cli.app import (
        _select_relevant_skills,
        _build_runtime_skill_context,
    )
    
    print("\n" + "=" * 60)
    print("UiPath Claude Code - Interactive Test Mode")
    print("=" * 60)
    print("Commands:")
    print("  /skills     - Show loaded skills")
    print("  /select     - Test skill selection for last prompt")
    print("  /quit       - Exit")
    print("=" * 60 + "\n")
    
    # Load skills
    registry = SkillRegistry()
    skills = registry.load_skills()
    print(f"Loaded {len(skills)} skills\n")
    
    # Create engine
    from uipath_claude.config import DEFAULT_BEDROCK_MODEL

    model_name = os.getenv("UIPATH_CLAUDE_MODEL", DEFAULT_BEDROCK_MODEL)
    region = os.getenv("AWS_REGION", "us-east-1")
    
    try:
        engine = ConversationEngine(model_name=model_name, region=region)
        print(f"Connected to {model_name}\n")
    except Exception as e:
        print(f"Error connecting to Bedrock: {e}")
        print("Make sure AWS credentials are configured.")
        return
    
    last_prompt = ""
    
    async def get_streaming_response(prompt, system_prompt):
        messages = [{"role": "user", "content": prompt}]
        def on_delta(delta):
            print(delta, end="", flush=True)
        await engine.run_stream(messages, tools=[], system_prompt=system_prompt, on_delta=on_delta)
    
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.lower() == "/quit":
            print("Goodbye!")
            break
        
        if user_input.lower() == "/skills":
            print("\nLoaded skills:")
            for s in skills:
                print(f"  - {s['name']}")
            print()
            continue
        
        if user_input.lower() == "/select":
            if last_prompt:
                test_skill_selection(last_prompt)
            else:
                print("No previous prompt to test.")
            print()
            continue
        
        last_prompt = user_input
        
        # Select skill
        selected_skills = _select_relevant_skills(user_input, skills, max_items=1)
        selected_skill = selected_skills[0]["name"] if selected_skills else None
        if selected_skill:
            print(f"[Skill: {selected_skill}]")
        
        # Build context
        skill_context = _build_runtime_skill_context(user_input, skills)
        
        system_prompt = "You are UiPath Claude Code. You build UiPath Studio automations."
        if skill_context:
            system_prompt += f"\n\n{skill_context}"
        
        # Get response
        print("\nAssistant: ", end="", flush=True)
        try:
            asyncio.run(get_streaming_response(user_input, system_prompt))
            print("\n")
        except Exception as e:
            print(f"\nError: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Test the conversational agent")
    parser.add_argument("--prompt", "-p", help="Single prompt to test")
    parser.add_argument("--test-skills", "-s", action="store_true", help="Test skill selection only")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming")
    args = parser.parse_args()
    
    if args.test_skills:
        # Test skill selection with sample prompts
        test_prompts = [
            "Create a UiPath workflow that reads emails from Outlook",
            "Build a coded workflow in C# to process Excel files",
            "Create a Flow project for document approval",
            "Help me with UI automation using servo",
            "Deploy my automation to Orchestrator",
        ]
        
        print("\n" + "=" * 60)
        print("Skill Selection Tests")
        print("=" * 60)
        
        for prompt in test_prompts:
            test_skill_selection(prompt)
            print()
        
    elif args.prompt:
        run_single_prompt(args.prompt, stream=not args.no_stream)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
