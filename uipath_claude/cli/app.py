"""CLI application entry point."""
import asyncio
from datetime import datetime, timezone
import os
import re
from pathlib import Path
import sys
import uuid
from typing import Any

import typer
from rich.console import Console
from rich.prompt import Prompt
from uipath_claude.commands.analyze import register_analyze_command
from uipath_claude.commands.bootstrap import register_bootstrap_command
from uipath_claude.commands.help import register_help_command
from uipath_claude.commands.plan import register_plan_command
from uipath_claude.commands.recall import register_recall_command
from uipath_claude.commands.repair_restore import register_repair_restore_command
from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.skills import register_skills_command
from uipath_claude.commands.status import register_status_command
from uipath_claude.commands.knowledge import register_knowledge_command
from uipath_claude.commands.resume import register_resume_command
from uipath_claude.commands.update_skills import register_update_skills_command
from uipath_claude.commands.validate import register_validate_command
from uipath_claude.commands.library_proposals import register_library_proposals_command
from uipath_claude.cli.capability_hint import maybe_print_capability_build_hint
from uipath_claude.context.project import detect_uipath_project
from uipath_claude.memory.loader import load_memory
from uipath_claude.artifacts.materialize import (
    contains_file_blocks,
    materialize_from_assistant_text,
    validate_generated_project,
)
from uipath_claude.query.bootstrap import run_bootstrap_flow
from uipath_claude.query.conversation import ConversationEngine
from uipath_claude.graph.builder import compile_chat_graph
from uipath_claude.config import DEFAULT_BEDROCK_MODEL
from uipath_claude.cli.documentation_flow import run_documentation_flow
from uipath_claude.query.doc_need_detector import DocNeedLevel, detect_documentation_need
from uipath_claude.query.intent_classifier import IntentType, classify_intent
from uipath_claude.query.plan_block import PLAN_BLOCK_HEADING, build_plan_block
from uipath_claude.query.planner import run_planner_agent
from uipath_claude.query.planner_router import find_planner_skill, should_use_planner
from uipath_claude.query.router import route_user_input
from uipath_claude.query.simple_answer import simple_llm_answer
from uipath_claude.skills.execution_hook import get_execution_hooks
from uipath_claude.rendering.branding import print_welcome_banner
from uipath_claude.rendering.progress import ProgressReporter
from uipath_claude.skills.loader import load_skill_content
from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.skills.updater import check_for_updates, ensure_fresh
from uipath_claude.sessions.store import SessionEvent, SessionStore
from uipath_claude.hooks.session_hooks import check_uip_installed
from uipath_claude.tools.profiles import is_command_allowed, resolve_tool_profile
from uipath_claude.tools.skill_tool import create_skill_tool
from uipath_claude.tools.skill_execution_tools import _get_output_root

import logging

logger = logging.getLogger(__name__)


def _load_dotenv_from_cwd() -> None:
    """Load ``.env`` from the current working directory.

    Keys starting with ``UIPATH_`` always take values from ``.env`` so a project file
    wins over stale User/Machine environment variables (common on Windows). Other
    keys are only set when not already present in the environment.
    """
    path = Path.cwd() / ".env"
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1]
        if key.startswith("UIPATH_") or key not in os.environ:
            os.environ[key] = val


app = typer.Typer(help="UiPath Claude Code - Conversational AI for UiPath")

register_library_proposals_command(app)

_UIPATH_CHAT_SYSTEM = f"""You are UiPath Claude Code, an agentic AI assistant with direct access to the user's local file system, UiPath CLI, and UiPath skills. You build UiPath Studio automations (workflow XAML), not WPF desktop apps, unless the user explicitly asks for WPF.

CRITICAL CAPABILITIES:
- You HAVE full capabilities to execute UiPath skills, read/write files, run CLI commands, and build automations directly on the user's machine.
- NEVER say you don't have access to tools, skills, or the local environment. You ARE an agentic assistant.
- When the user asks you to do something, DO IT using your tools (if in agentic mode) or by generating the necessary files.

EXECUTING APPROVED IMPLEMENTATION PLANS:
If the runtime context includes a "{PLAN_BLOCK_HEADING}" section (markdown `## {PLAN_BLOCK_HEADING}` or legacy plain prefix), treat it as your execution checklist—not background prose.
You MUST carry it out with tools and/or UIPATH_FILE blocks until the user's build request is satisfied (or you hit a hard blocker you report clearly).
1. Read every plan step; map vague steps to concrete tools (e.g. scaffold → `ensure_project_structure`, new XAML → `write_file` or file blocks).
2. Prefer tool calls over narration; do not end the turn having only summarized the plan.
3. If the plan mentions human-only steps (e.g. "open Studio"), substitute the closest supported automation (project structure, XAML files, validation) and continue.

Example translations:
- "Create project / use uip new" → call `ensure_project_structure` (or equivalent) for the target project directory, then add workflows.
- "Add Main.xaml" → `write_file` or `<<<UIPATH_FILE path="Main.xaml">>>` blocks with valid XAML.
- "Validate workflow" → `validate_and_fix_loop` on the XAML path when available.

Do not reply that the plan "looks good" or that you lack access—execute.

IMPORTANT - Clarification Before Action:
If the user's request is ambiguous, vague, or missing critical details needed to build a correct workflow, ASK for clarification BEFORE generating any files. Examples of when to ask:
- "automate email" - Ask: What email provider? Read or send? What should happen with the emails?
- "process data" - Ask: What data source? What processing? What output?
- "click button" - Ask: Which application? What button? What should happen after?
- "integrate with X" - Ask: What specific operations? Read/write/both? What data?

Do NOT guess or make assumptions about critical workflow logic. It's better to ask one clarifying question than to generate a workflow that doesn't match the user's needs.

If a UiPath project already exists, do not regenerate scaffold files (`project.json`, `project.uiproj`, `.local`, `.objects`) unless the user explicitly asks.
When the user asks for a workflow, default to writing only `.xaml` workflow files.
Do not invent or pin legacy dependency versions in `project.json`; if package changes are required, explain the `uip rpa install-or-update-packages` command instead.

When the user asks you to CREATE, WRITE, or GENERATE files, you MUST include one or more file blocks using EXACTLY this format (markers on their own lines; path uses forward slashes only):

<<<UIPATH_FILE path="Main.xaml">>>
...complete file body...
<<<END_UIPATH_FILE>>>

Put files under logical subpaths (e.g. `demo/Main.xaml`). Use only relative paths; no `..` segments.
You may instead use a markdown code fence whose first line is exactly: path: <relative/path> then the file body on following lines until the closing fence.

After the blocks you may add one short sentence summarizing what you wrote."""

_SKILL_CONTEXT_MAX_CHARS = 20000  # Increased to include critical sections
_SKILL_CONTEXT_MAX_ITEMS = 2

# Intent detection tokens - used for dynamic skill matching
# These are user-intent keywords, NOT skill names (skills may change)
_RPA_HINT_TOKENS = {
    "uipath",
    "workflow",
    "workflows",
    "xaml",
    "automation",
    "outlook",
    "email",
    "excel",
    "browser",
    "selector",
    "queue",
    "mail",
}
_CODED_HINT_TOKENS = {"coded", "csharp", "c#", ".cs"}
_DOC_INTENT_TOKENS = {"pdd", "sdd", "document", "architecture", "design"}
_FLOW_HINT_TOKENS = {"flow", "maestro", "agentic"}
_PLATFORM_HINT_TOKENS = {"orchestrator", "deploy", "connector", "integration service"}

_SKILL_SELECTION_MIN_SCORE = 2

# Dynamic skill category detection patterns
# These patterns match skill metadata (name, description, triggers) to detect category
# Order matters - more specific patterns should come first
_SKILL_CATEGORY_PATTERNS = {
    "pdd": ["pdd", "process definition document"],
    "sdd": ["sdd", "solution design"],
    "flow": ["flow", "maestro"],
    "platform": ["platform", "orchestrator"],
    "coded": ["coded workflow", "csharp", ".cs file"],
    "rpa": ["rpa", "xaml", "uipath workflow"],  # More specific patterns
}

# Legacy skill name aliases - maps old names to canonical category
# This allows graceful handling when skill names change
_SKILL_NAME_ALIASES = {
    "uipath-rpa-workflows": "uipath-rpa",
    "uipath-automation": "uipath-rpa",
    "uipath-coded-workflows": "uipath-rpa",  # Now part of uipath-rpa
}

_PROJECT_FILE_HINTS = {
    "project.json",
    "project.uiproj",
    "create project",
    "new project",
    "scaffold",
    "template",
}
_FILE_INTENT_TOKENS = {
    "build",
    "create",
    "generate",
    "write",
    "make",
    "workflow",
    "xaml",
    "project",
    "file",
    "files",
}


def _save_plan_to_file(
    session_id: str,
    user_request: str,
    plan_content: str,
    output_root: Path,
) -> Path:
    """Save approved plan to .plan.md file."""
    session_dir = output_root / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    plan_path = session_dir / ".plan.md"

    content = f"""# Implementation Plan
Generated: {datetime.now(timezone.utc).isoformat()}
Session: {session_id}

## User Request
{user_request}

## Plan
{plan_content}
"""
    try:
        plan_path.write_text(content, encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to save plan to %s: %s", plan_path, e)
    return plan_path


def _tokenize(text: str) -> set[str]:
    """Tokenize text for lightweight lexical scoring."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _canonical_skill_name(name: str) -> str:
    """Normalize legacy skill names to canonical routing names."""
    normalized = name.strip().lower()
    return _SKILL_NAME_ALIASES.get(normalized, normalized)


def _is_better_skill_candidate(
    current: tuple[int, dict],
    candidate: tuple[int, dict],
    canonical_name: str,
) -> bool:
    """Choose highest score; prefer canonical name for ties."""
    current_score, current_skill = current
    candidate_score, candidate_skill = candidate
    if candidate_score != current_score:
        return candidate_score > current_score
    current_name = str(current_skill.get("name", "")).strip().lower()
    candidate_name = str(candidate_skill.get("name", "")).strip().lower()
    if candidate_name == canonical_name and current_name != canonical_name:
        return True
    if current_name == canonical_name and candidate_name != canonical_name:
        return False
    return candidate_name < current_name


def _detect_skill_category(skill: dict) -> str | None:
    """Dynamically detect skill category from metadata (name, description, triggers).
    
    This allows the system to work even when skill names change in the UiPath repo.
    Priority: skill name > triggers > description (name is most reliable indicator)
    """
    name = str(skill.get("name", "")).lower()
    description = str(skill.get("description", "")).lower()
    triggers = skill.get("triggers", [])
    trigger_text = " ".join(str(t).lower() for t in triggers if t)
    
    # Check name first (most reliable)
    for category, patterns in _SKILL_CATEGORY_PATTERNS.items():
        if any(pattern in name for pattern in patterns):
            return category
    
    # Check triggers second
    for category, patterns in _SKILL_CATEGORY_PATTERNS.items():
        if any(pattern in trigger_text for pattern in patterns):
            return category
    
    # Check description last (least reliable, may have false positives)
    for category, patterns in _SKILL_CATEGORY_PATTERNS.items():
        if any(pattern in description for pattern in patterns):
            return category
    
    return None


def _preferred_rpa_skill(skills: list[dict]) -> dict | None:
    """Return best RPA skill - uses dynamic category detection.
    
    Prefers skills that match the 'rpa' category pattern, falling back to
    any skill with 'rpa' in the name or description.
    """
    rpa_skills = [s for s in skills if _detect_skill_category(s) == "rpa"]
    if rpa_skills:
        rpa_skills.sort(key=lambda s: str(s.get("name", "")).lower())
        return rpa_skills[0]
    
    # Fallback: any skill with rpa/workflow in name
    fallback = [s for s in skills if "rpa" in str(s.get("name", "")).lower() 
                or "workflow" in str(s.get("name", "")).lower()]
    if fallback:
        fallback.sort(key=lambda s: str(s.get("name", "")).lower())
        return fallback[0]
    
    return None


def _score_skill(skill: dict, user_input: str, user_tokens: set[str]) -> int:
    """Compute relevance score between user prompt and skill metadata.
    
    Uses dynamic category detection instead of hardcoded skill names,
    making it resilient to skill name changes in the UiPath repo.
    """
    name = str(skill.get("name", ""))
    description = str(skill.get("description", ""))
    triggers = skill.get("triggers", [])
    lower_input = user_input.lower()
    
    # Detect skill category dynamically
    category = _detect_skill_category(skill)

    score = 0
    
    # Base scoring from name and description token overlap
    score += len(_tokenize(name) & user_tokens) * 4
    score += len(_tokenize(description) & user_tokens) * 2

    # Trigger matching (from skill metadata)
    if isinstance(triggers, list):
        for trigger in triggers:
            trig = str(trigger).strip().lower()
            if not trig:
                continue
            if trig in lower_input:
                score += 6
            else:
                score += len(_tokenize(trig) & user_tokens)

    # Intent detection from user input
    is_coded_intent = (
        ".cs" in lower_input
        or "coded workflow" in lower_input
        or "c#" in lower_input
        or bool(user_tokens & _CODED_HINT_TOKENS)
    )
    is_doc_intent = bool(user_tokens & _DOC_INTENT_TOKENS)
    is_flow_intent = bool(user_tokens & _FLOW_HINT_TOKENS)
    is_platform_intent = bool(user_tokens & _PLATFORM_HINT_TOKENS)

    # Category-based scoring boosts (dynamic, not hardcoded to skill names)
    if category == "coded" and is_coded_intent:
        score += 20
    elif category == "pdd" and ("pdd" in user_tokens or "process definition" in lower_input):
        score += 20
    elif category == "sdd" and ("sdd" in user_tokens or "solution design" in lower_input):
        score += 20
    elif category == "flow" and is_flow_intent:
        score += 15
    elif category == "platform" and is_platform_intent:
        score += 15
    elif category == "rpa":
        # RPA is the default for workflow requests, but deprioritize for coded/doc intents
        if is_coded_intent or is_doc_intent:
            score -= 10
        elif user_tokens & _RPA_HINT_TOKENS:
            score += 12

    return score


def _is_workflow_intent(user_input: str, user_tokens: set[str]) -> bool:
    """Detect likely RPA workflow requests."""
    lower = user_input.lower()
    is_coded_intent = (
        ".cs" in lower
        or "coded workflow" in lower
        or "c#" in lower
        or ("coded" in user_tokens and "workflow" in user_tokens)
    )
    if is_coded_intent:
        return False
    if user_tokens & _DOC_INTENT_TOKENS:
        return False
    has_explicit_workflow_terms = bool({"workflow", "workflows", "xaml"} & user_tokens)
    if has_explicit_workflow_terms:
        return True
    return bool(user_tokens & _RPA_HINT_TOKENS)


def _select_relevant_skills(user_input: str, skills: list[dict], max_items: int = 2) -> list[dict]:
    """Select the most relevant skills for a free-form chat request."""
    user_tokens = _tokenize(user_input)
    if not user_tokens:
        return []

    top_score = 0
    if skills:
        top_score = max(_score_skill(s, user_input, user_tokens) for s in skills)
    use_planner, _planner_reason = should_use_planner(user_input, top_score)
    if use_planner:
        planner_skill = find_planner_skill(skills)
        if planner_skill:
            return [planner_skill][:max_items]

    ranked: dict[str, tuple[int, dict]] = {}
    for skill in skills:
        score = _score_skill(skill, user_input, user_tokens)
        if score < _SKILL_SELECTION_MIN_SCORE:
            continue
        canonical = _canonical_skill_name(str(skill.get("name", "")))
        existing = ranked.get(canonical)
        candidate = (score, skill)
        if existing is None or _is_better_skill_candidate(existing, candidate, canonical):
            ranked[canonical] = candidate

    sorted_ranked = sorted(
        ranked.items(),
        key=lambda item: (
            -item[1][0],
            item[0],
            str(item[1][1].get("name", "")).strip().lower(),
        ),
    )
    selected = [skill for _, (_, skill) in sorted_ranked[:max_items]]

    if _is_workflow_intent(user_input, user_tokens):
        rpa_skill = _preferred_rpa_skill(skills)
        if rpa_skill:
            rpa_skill_name = str(rpa_skill.get("name", "")).lower()
            selected = [
                rpa_skill,
                *[
                    s
                    for s in selected
                    if str(s.get("name", "")).lower() != rpa_skill_name
                ],
            ][:max_items]

    return selected


def _debug_skill_selection(user_input: str, skills: list[dict]) -> list[str]:
    """Return human-readable skill score traces for diagnostics."""
    user_tokens = _tokenize(user_input)
    scored: list[tuple[int, str, str]] = []
    for skill in skills:
        name = str(skill.get("name", ""))
        canonical = _canonical_skill_name(name)
        display_name = canonical if canonical == name else f"{name} -> {canonical}"
        scored.append((_score_skill(skill, user_input, user_tokens), display_name, name))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [f"{name}: {score}" for score, name, _ in scored[:5] if score >= _SKILL_SELECTION_MIN_SCORE]


def _snapshot_files(root: Path) -> dict[str, tuple[int, int]]:
    """Capture a shallow file fingerprint for auto-fix loop stopping."""
    snapshot: dict[str, tuple[int, int]] = {}
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            stat = file_path.stat()
        except OSError:
            continue
        snapshot[str(file_path.relative_to(root))] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def _extract_critical_sections(skill_content: str) -> str:
    """
    Extract CRITICAL sections from skill content for priority injection.
    
    CRITICAL sections are marked with ### CRITICAL: in markdown.
    These are placed at the top of the skill content to ensure the LLM sees them.
    """
    lines = skill_content.split('\n')
    critical_lines = []
    in_critical = False
    current_section = []
    
    for line in lines:
        # Start of a new CRITICAL section
        if '### CRITICAL:' in line or line.strip().startswith('### CRITICAL'):
            # Save previous section if any
            if current_section:
                critical_lines.extend(current_section)
                critical_lines.append('')  # Add blank line between sections
            in_critical = True
            current_section = [line]
        elif in_critical:
            # End of critical section when we hit another ### heading (not CRITICAL)
            if line.startswith('###') and 'CRITICAL' not in line:
                critical_lines.extend(current_section)
                critical_lines.append('')
                in_critical = False
                current_section = []
            # Also end on ## heading (higher level)
            elif line.startswith('## '):
                critical_lines.extend(current_section)
                critical_lines.append('')
                in_critical = False
                current_section = []
            else:
                current_section.append(line)
    
    # Don't forget the last section
    if current_section:
        critical_lines.extend(current_section)
    
    return '\n'.join(critical_lines) if critical_lines else ""


def _build_runtime_skill_context_for_selected(
    _user_input: str, selected: list[dict]
) -> str:
    """Build skill markdown for an explicit skill subset (used by LangGraph execute)."""
    if not selected:
        return ""

    sections: list[str] = [
        "Use the following skill guidance for this request. Follow these rules strictly."
    ]
    hooks = get_execution_hooks(Path.cwd())
    for skill in selected:
        name = str(skill.get("name", "unknown"))
        content = load_skill_content(str(skill.get("path", "")))
        if not content:
            continue

        critical = _extract_critical_sections(content)
        if critical:
            sections.append(f"[Skill: {name} - CRITICAL RULES]\n{critical}")

        insights_summary = hooks.get_insights_summary(name, max_tokens=150)
        if insights_summary.strip():
            sections.append(f"[Skill: {name} - Learned from Usage]\n{insights_summary.strip()}")

        trimmed = content[:_SKILL_CONTEXT_MAX_CHARS]
        sections.append(f"[Skill: {name}]\n{trimmed}")

    return "\n\n".join(sections)


def _build_runtime_skill_context(user_input: str, skills: list[dict]) -> str:
    """Build request-scoped skill guidance injected into the model prompt."""
    selected = _select_relevant_skills(
        user_input, skills, max_items=_SKILL_CONTEXT_MAX_ITEMS
    )
    return _build_runtime_skill_context_for_selected(user_input, selected)


def _make_chat_session_id() -> str:
    """Create a traceable chat session identifier."""
    override = os.environ.get("UIPATH_CHAT_SESSION_ID", "").strip()
    if override:
        safe = re.sub(r"[^A-Za-z0-9._-]", "-", override)
        return safe or "chat-session"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _allow_project_file_generation(user_input: str) -> bool:
    """Only allow chat writes for project files when explicitly requested."""
    lower = user_input.lower()
    return any(hint in lower for hint in _PROJECT_FILE_HINTS)


def _is_file_generation_intent(user_input: str) -> bool:
    """Detect whether the user likely expects generated files.

    Pure QUESTION intents (e.g. asking what project.json is) often match tokens like
    ``project`` or ``file`` but are not file-generation requests; treating them as
    file intent incorrectly sets ``suppress_stream_output`` under default streaming.
    """
    intent, _ = classify_intent(user_input)
    if intent == IntentType.QUESTION:
        return False
    tokens = _tokenize(user_input)
    return bool(tokens & _FILE_INTENT_TOKENS)


def _resolve_output_mode() -> str:
    """
    Resolve chat output mode for assistant responses.

    Modes:
    - auto: suppress file-heavy responses
    - quiet: always suppress assistant body
    - full: always print assistant body
    """
    mode = os.environ.get("UIPATH_CHAT_OUTPUT_MODE", "auto").strip().lower()
    if mode in {"quiet", "full"}:
        return mode
    return "auto"


def _is_generated_chat_artifact_folder(path: Path) -> bool:
    """Identify generated/chat output folders to prevent project-open confusion."""
    normalized = [part.lower() for part in path.resolve().parts]
    for index, part in enumerate(normalized):
        if part == "generated" and index + 1 < len(normalized) and normalized[index + 1] == "chat":
            return True
    return False


def _build_command_registry(
    skill_registry: SkillRegistry,
    get_status,
    get_history,
    run_planner=None,
) -> CommandRegistry:
    """Create and register built-in slash commands."""
    registry = CommandRegistry()
    register_help_command(registry)
    register_status_command(registry, get_status=get_status)
    register_skills_command(
        registry,
        list_skills=skill_registry.load_skills,
        filter_skills_by_role=skill_registry.filter_by_agent,
    )
    register_analyze_command(registry)
    register_validate_command(registry)
    register_repair_restore_command(registry)
    register_bootstrap_command(registry, run_bootstrap=run_bootstrap_flow)
    register_update_skills_command(registry)
    register_recall_command(registry, get_history=get_history)
    if run_planner:
        register_plan_command(registry, run_planner=run_planner)
    return registry


def _create_engine() -> ConversationEngine:
    """Create Bedrock conversation engine from environment settings."""
    model_name = os.getenv("UIPATH_CLAUDE_MODEL", DEFAULT_BEDROCK_MODEL)
    region = os.getenv("AWS_REGION", "us-east-1")
    return ConversationEngine(model_name=model_name, region=region)


async def _get_model_response(
    engine: ConversationEngine,
    history: list[dict[str, str]],
    memory: str,
    runtime_context: str = "",
    *,
    stream: bool = False,
    on_delta=None,
) -> str:
    """Get an LLM response from Bedrock conversation engine."""
    base = _UIPATH_CHAT_SYSTEM
    context_parts = [base]
    if memory:
        context_parts.append(f"Memory:\n{memory}")
    if runtime_context:
        context_parts.append(f"Runtime guidance:\n{runtime_context}")
    context_prompt = "\n\n".join(context_parts)
    messages = [{"role": "system", "content": context_prompt}, *history]
    if stream:
        return await engine.run_stream(
            messages=messages,
            tools=[],
            system_prompt=context_prompt,
            on_delta=on_delta,
        )
    return await engine.run(messages=messages, tools=[], system_prompt=context_prompt)


def _parse_numbered_questions_from_clarifier(text: str) -> list[str]:
    """Split clarifier output into numbered questions (lines like ``1. ...`` or ``2) ...``)."""
    out: list[str] = []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if m:
            out.append(m.group(1).strip())
    return out


@app.command()
def chat(
    no_banner: bool = typer.Option(False, "--no-banner", help="Skip welcome banner"),
    no_plan: bool = typer.Option(False, "--no-plan", help="Skip planning phase for BUILD intents"),
    auto_approve_plan: bool = typer.Option(
        False,
        "--auto-approve-plan",
        help="Auto-approve plans without prompting (for CI/testing)",
    ),
    stream: bool | None = typer.Option(
        None,
        "--stream/--no-stream",
        help="Stream assistant tokens while generating responses.",
    ),
    track_processes: bool = typer.Option(True, "--track-processes/--no-track-processes", help="Track and cleanup only test-opened Studio processes"),
):
    """Start conversational chat mode."""
    _load_dotenv_from_cwd()
    console = Console()
    progress = ProgressReporter(console)

    def _stdio_line_buffered() -> None:
        """When stdout is a pipe (e.g. eval subprocess), avoid block buffering."""
        for stream in (sys.stdout, sys.stderr):
            reconf = getattr(stream, "reconfigure", None)
            if callable(reconf) and hasattr(stream, "isatty") and not stream.isatty():
                try:
                    reconf(line_buffering=True)
                except (OSError, ValueError, TypeError, AttributeError):
                    pass

    def _flush_stdio() -> None:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass

    _stdio_line_buffered()

    if os.environ.get("UIPATH_SKILLS_AUTO_REFRESH", "1").strip().lower() in ("1", "true", "yes"):
        try:
            msg = ensure_fresh(max_age_seconds=6 * 3600)
            if msg.startswith("updated"):
                console.print(f"[dim]Skills cache: {msg}[/dim]")
        except Exception:
            pass

    try:
        from uipath_claude.skills.retirement_scheduler import maybe_run_retirement_scheduled

        maybe_run_retirement_scheduled()
    except Exception:
        pass

    # Track processes before starting (for smart cleanup)
    before_pids = None
    if track_processes:
        try:
            from uipath_claude.utils.process_tracker import start_tracking_test
            before_pids = start_tracking_test()
        except Exception:
            pass  # Process tracking is optional
    
    if not no_banner:
        print_welcome_banner()
    
    project_context = detect_uipath_project(str(Path.cwd()))
    if project_context:
        console.print(f"Detected UiPath project: {project_context['project_name']}\n")
    cwd = Path.cwd().resolve()
    if _is_generated_chat_artifact_folder(cwd) and (cwd / "project.json").exists():
        progress.warning(
            "This looks like a generated chat artifact folder. "
            "Open your real UiPath project root for package restore/build."
        )
        console.print("")
    
    memory = load_memory(
        project_path=project_context["project_path"] if project_context else None
    )

    # Check for skills updates (non-blocking)
    try:
        has_updates, update_msg, _, _ = check_for_updates()
        if has_updates:
            progress.info("Skills update available. Run /update-skills to update.")
            console.print("")
    except Exception:
        pass  # Don't block startup on update check failures
    
    # Check uip CLI installation
    try:
        uip_ok, uip_msg = check_uip_installed()
        if not uip_ok:
            progress.warning(uip_msg)
            console.print("")
    except Exception:
        pass
    
    # Check UiPath CLI authentication status (skip if running automated tests)
    skip_auth_check = os.getenv("UIPATH_SKIP_AUTH_CHECK", "0").lower() in ("1", "true", "yes")
    
    if not skip_auth_check:
        try:
            from uipath_claude.utils.auth_check import (
                check_uipath_cli_installed,
                check_uipath_auth_status,
                prompt_for_authentication,
                resolve_uipath_auth_argv,
                run_uipath_interactive_auth,
            )
            
            # Check if CLI is installed
            if not check_uipath_cli_installed():
                progress.warning(
                    "UiPath CLI not found. Deployment features will not be available.\n"
                    "Install from: https://docs.uipath.com/automation-cloud/automation-cloud/latest/admin-guide/managing-automation-suite-using-the-cli"
                )
                console.print("")
            else:
                # Check authentication status
                is_authenticated, account, error = check_uipath_auth_status()
            
                if not is_authenticated:
                    # Prompt user to authenticate
                    orchestrator_url = os.getenv("UIPATH_ORCHESTRATOR_URL")
                    auth_choice = prompt_for_authentication(console, orchestrator_url)

                    if auth_choice == "skip_auth":
                        progress.warning(
                            "Continuing without authentication. "
                            "Deployment features disabled."
                        )
                        console.print("")
                    else:
                        argv, argv_err = resolve_uipath_auth_argv(orchestrator_url)
                        if argv is None:
                            console.print(f"\n[red]{argv_err}[/red]\n")
                            raise typer.Exit(code=1)
                        rc = run_uipath_interactive_auth(console, argv)
                        if rc != 0:
                            console.print(
                                f"\n[red]uipath auth exited with code {rc}. "
                                "Check UIPATH_TENANT_NAME and UIPATH_ORCHESTRATOR_URL against "
                                "your Automation Cloud tenant (e.g. messages like "
                                "'Tenant not found' mean the name does not match the portal). "
                                "Then try again.[/red]\n"
                            )
                            raise typer.Exit(code=1)
                        is_authenticated, account, verify_err = check_uipath_auth_status()
                        if is_authenticated:
                            if account:
                                console.print(
                                    f"\n[green]Authenticated as: {account}[/green]\n"
                                )
                            else:
                                console.print(
                                    "\n[green]Authenticated with UiPath Orchestrator.[/green]\n"
                                )
                        else:
                            progress.warning(
                                "Auth command finished, but Orchestrator verification "
                                f"still failed: {verify_err or 'unknown error'}. "
                                "Deployment may not work until this succeeds."
                            )
                            console.print("")
                else:
                    # Authenticated - show brief status
                    if account:
                        console.print(f"[dim]Authenticated as: {account}[/dim]\n")
                    else:
                        console.print(
                            "[dim]Authenticated with UiPath Orchestrator[/dim]\n"
                        )
        except typer.Exit:
            # User chose "exit and authenticate"; typer.Exit subclasses Exception — re-raise
            raise
        except Exception as e:
            # Don't block startup on auth check failures
            progress.warning(f"Could not verify authentication: {e}")
            console.print("")
    
    skill_registry = SkillRegistry()
    model_name = os.getenv("UIPATH_CLAUDE_MODEL", DEFAULT_BEDROCK_MODEL)
    region = os.getenv("AWS_REGION", "us-east-1")
    tool_profile = resolve_tool_profile(os.getenv("UIPATH_CLAUDE_TOOL_PROFILE", "safe"))
    skills = skill_registry.load_skills()
    skills_by_name = {skill.get("name"): skill for skill in skills}
    history: list[dict[str, str]] = []

    def _status() -> dict[str, str | int | bool]:
        return {
            "model": model_name,
            "region": region,
            "project_detected": bool(project_context),
            "project_name": project_context["project_name"] if project_context else "n/a",
            "memory_loaded": bool(memory),
            "skill_count": len(skills),
            "tool_profile": tool_profile.name,
        }

    def _history() -> list[dict[str, str]]:
        return history

    def _run_planner(description: str) -> str:
        """Synchronous wrapper for the async planner agent."""
        result = asyncio.run(
            run_planner_agent(
                description,
                project_context=project_context,
                model_name=model_name,
                region=region,
            )
        )
        return result.final_response

    registry = _build_command_registry(skill_registry, _status, _history, run_planner=_run_planner)
    register_resume_command(registry)
    register_knowledge_command(registry, Path.cwd().resolve())

    try:
        engine = _create_engine()
    except Exception as exc:
        progress.error("Could not initialize Bedrock model")
        console.print(
            "Set AWS credentials and region, then retry. "
            "Example: set AWS_REGION=us-east-1."
        )
        raise typer.Exit(code=1) from exc

    stream_hooks: dict[str, Any] = {"on_delta": None}
    clarification_prefix = ""

    async def run_model_for_graph(
        messages: list[dict[str, str]], runtime: str, stream: bool
    ) -> str:
        return await _get_model_response(
            engine,
            messages,
            memory,
            runtime,
            stream=stream,
            on_delta=stream_hooks["on_delta"] if stream else None,
        )

    from uipath_claude.tools.skill_execution_tools import get_skill_execution_tools

    agentic_tools = get_skill_execution_tools()

    console.print("Chat session started. Type 'exit' or 'quit' to leave.\n")
    stream_enabled = _resolve_stream_enabled(stream)
    output_mode = _resolve_output_mode()
    session_store = SessionStore()
    env_sid = os.environ.get("UIPATH_CHAT_SESSION_ID", "").strip()
    if env_sid:
        chat_session_id = re.sub(r"[^A-Za-z0-9._-]", "-", env_sid) or session_store.new_session_id()
    else:
        chat_session_id = session_store.new_session_id()
    os.environ["UIPATH_CHAT_SESSION_ID"] = chat_session_id
    (_get_output_root() / chat_session_id).mkdir(parents=True, exist_ok=True)
    console.print(f"[dim]Session: {chat_session_id}[/dim]\n")

    from uipath_claude.tools.approval import ApprovalDecision, ApprovalPolicy

    approval_policy: ApprovalPolicy | None = None
    # Default "1": prompt for destructive tools. Opt out with 0 / false / no (e.g. CI).
    _skip_approval_prompts = os.environ.get("UIPATH_TOOL_APPROVAL", "1").strip().lower() in (
        "0",
        "false",
        "no",
    )
    if not _skip_approval_prompts:

        def _approval_prompter(tool_name: str, _tool_args: dict) -> ApprovalDecision:
            if not sys.stdin.isatty():
                return ApprovalDecision.DENY
            choice = (
                Prompt.ask(
                    f"Allow destructive tool `{tool_name}`? [once/always/deny]",
                    default="once",
                )
                .strip()
                .lower()
            )
            if choice in ("always", "a"):
                return ApprovalDecision.ALLOW_ALWAYS
            if choice in ("deny", "d", "no", "n"):
                return ApprovalDecision.DENY
            return ApprovalDecision.ALLOW_ONCE

        approval_policy = ApprovalPolicy(prompter=_approval_prompter)

    chat_graph = compile_chat_graph(
        skills,
        select_skills_fn=lambda u: _select_relevant_skills(
            u, skills, max_items=_SKILL_CONTEXT_MAX_ITEMS
        ),
        build_runtime_for_selected=_build_runtime_skill_context_for_selected,
        run_model=run_model_for_graph,
        default_stream=False,
        agentic_tools=agentic_tools,
        model_name=model_name,
        region=region,
        approval_policy=approval_policy,
        session_logging=(session_store, chat_session_id),
    )

    try:
        while True:
            try:
                user_input = Prompt.ask("[cyan]You[/cyan]").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"}:
                console.print("Goodbye!")
                break

            route, payload = route_user_input(user_input)
            if route == "command":
                command = payload["command"]
                args = payload["args"]
                if command == "chat":
                    console.print("You are already in chat mode.")
                    continue
                if command in {"exit", "quit"}:
                    console.print("Goodbye!")
                    break
                if not is_command_allowed(tool_profile, command):
                    progress.error(
                        f"Command '/{command}' is blocked by tool profile '{tool_profile.name}'. "
                        "Use /status to inspect active profile."
                    )
                    continue
                console.print(registry.execute(command, *args))
                continue
            if route == "skill_usage":
                console.print("Usage: /skill <skill-name> <query>")
                continue
            if route == "skill":
                skill_name = payload["skill_name"]
                query = payload["query"]
                if not is_command_allowed(tool_profile, "skills"):
                    progress.error(
                        f"Command '/skill' is blocked by tool profile '{tool_profile.name}'. "
                        "Use /status to inspect active profile."
                    )
                    continue
                skill = skills_by_name.get(skill_name)
                if not skill:
                    progress.error(f"Unknown skill: {skill_name}")
                    continue
                tool = create_skill_tool(skill, engine=engine)
                result = tool.invoke({"query": query})
                console.print(f"[magenta]Assistant:[/magenta] {result}\n")
                continue

            intent, intent_reason = classify_intent(user_input)
            if os.environ.get("UIPATH_CONFIRM_BUILD", "0").strip().lower() in (
                "1",
                "true",
                "yes",
            ):
                if intent in (IntentType.BUILD, IntentType.AMBIGUOUS):
                    preview = _select_relevant_skills(user_input, skills)
                    preview_names = ", ".join(str(s.get("name", "")) for s in preview) or "(none)"
                    console.print(f"[yellow]Planned skills:[/yellow] {preview_names}")
                    console.print(f"[yellow]Intent:[/yellow] {intent.value} ({intent_reason})")
                    confirm = Prompt.ask(
                        "Proceed? [y/n or type details]",
                        default="y",
                    ).strip()
                    cl = confirm.lower()
                    if cl in ("n", "no"):
                        progress.info("Cancelled.")
                        continue
                    if cl not in ("", "y", "yes"):
                        user_input = f"{user_input}\n\nAdditional details from user: {confirm}"

            if intent == IntentType.DOCUMENTATION:
                console.print("[bold cyan][DOCUMENTATION][/bold cyan]")
                _flush_stdio()
                project_path = (
                    project_context["project_path"]
                    if project_context
                    else str(Path.cwd())
                )
                _created, reply = asyncio.run(
                    run_documentation_flow(
                        user_input=user_input,
                        history=history,
                        project_path=project_path,
                        session_id=chat_session_id,
                        model_name=model_name,
                        region=region,
                        progress=progress,
                    )
                )
                console.print(f"[magenta]Assistant:[/magenta] {reply}\n")
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": reply})
                continue

            # QUESTION intents bypass planning and agentic graph
            if intent == IntentType.QUESTION:
                console.print("[bold cyan][ANSWERING][/bold cyan]")
                _flush_stdio()
                
                def _print_delta(delta: str) -> None:
                    console.print(delta, end="")
                
                stream_callback = _print_delta if stream_enabled else None
                console.print("[magenta]Assistant:[/magenta] ", end="")
                
                try:
                    answer = asyncio.run(
                        simple_llm_answer(
                            user_input=user_input,
                            history=history,
                            model_name=model_name,
                            region=region,
                            stream=stream_enabled,
                            on_delta=stream_callback,
                        )
                    )
                    if not stream_enabled:
                        console.print(answer, end="")
                    console.print("")

                    maybe_print_capability_build_hint(console, user_input)

                    history.append({"role": "user", "content": user_input})
                    history.append({"role": "assistant", "content": answer})

                    continue
                except Exception as exc:
                    progress.error("Simple answer failed")
                    console.print(f"Error: {exc}")
                    continue

            if intent in (IntentType.BUILD, IntentType.AMBIGUOUS):
                doc_need = detect_documentation_need(user_input)
                if (
                    doc_need.recommended_docs
                    and doc_need.level
                    in (DocNeedLevel.RECOMMENDED, DocNeedLevel.REQUIRED)
                ):
                    default = "y" if doc_need.level == DocNeedLevel.REQUIRED else "n"
                    doc_label = ", ".join(d.upper() for d in doc_need.recommended_docs)
                    choice = Prompt.ask(
                        f"Documentation [{doc_need.level.value}]. "
                        f"Generate {doc_label} before coding?",
                        choices=["y", "n"],
                        default=default,
                    )
                    if choice.strip().lower() in ("y", "yes"):
                        project_path = (
                            project_context["project_path"]
                            if project_context
                            else str(Path.cwd())
                        )
                        _pre_docs, doc_reply = asyncio.run(
                            run_documentation_flow(
                                user_input=user_input,
                                history=history,
                                project_path=project_path,
                                session_id=chat_session_id,
                                model_name=model_name,
                                region=region,
                                progress=progress,
                            )
                        )
                        if doc_reply.strip():
                            console.print(
                                f"[magenta]Assistant (documentation):[/magenta] {doc_reply}\n"
                            )

            # Plan Mode logic
            approved_plan = ""
            plan_mode_enabled = os.environ.get("UIPATH_PLAN_MODE", "1").strip().lower() in ("1", "true", "yes")
            if plan_mode_enabled and not no_plan:
                if intent in (IntentType.BUILD, IntentType.AMBIGUOUS):
                    while True:
                        console.print("[bold cyan][PLANNING][/bold cyan]")
                        _flush_stdio()
                        with progress.generating("implementation plan"):
                            plan_result = asyncio.run(
                                run_planner_agent(
                                    user_input,
                                    project_context=project_context,
                                    model_name=model_name,
                                    region=region,
                                )
                            )
                    
                        from rich.markdown import Markdown
                        from rich.panel import Panel
                        console.print(Panel(Markdown(plan_result.final_response), title="Implementation Plan", border_style="cyan"))
                    
                        force_interactive = os.environ.get(
                            "UIPATH_FORCE_INTERACTIVE", "0"
                        ).strip().lower() in ("1", "true", "yes")
                        is_interactive = force_interactive or sys.stdin.isatty()
                        if auto_approve_plan or not is_interactive:
                            console.print("[dim]Auto-approving plan (non-interactive mode)[/dim]")
                            confirm = "y"
                        else:
                            console.print(
                                "[dim]Type 'y' to approve, 'n' to cancel, 'e'/'edit' to revise, "
                                "or describe changes to revise "
                                '(e.g. \"add Try/Catch around the log\").[/dim]'
                            )
                            raw_confirm = Prompt.ask(
                                "Approve plan? \\[y/n/edit]", default="y"
                            ).strip()
                            confirm = raw_confirm.lower()
                        if confirm in ("y", "yes", ""):
                            approved_plan = plan_result.final_response
                            # Save plan to file
                            plan_path = _save_plan_to_file(
                                session_id=chat_session_id,
                                user_request=user_input,
                                plan_content=approved_plan,
                                output_root=_get_output_root(),
                            )
                            console.print(f"[dim]Plan saved to: {plan_path}[/dim]")
                            break
                        elif confirm in ("n", "no"):
                            progress.info("Plan cancelled.")
                            break
                        elif confirm in ("e", "edit"):
                            feedback = Prompt.ask(
                                "What should change? (describe revisions)"
                            ).strip()
                            if not feedback:
                                console.print(
                                    "[dim]No feedback provided; showing plan again.[/dim]"
                                )
                                continue
                            user_input = f"{user_input}\n\nFeedback on plan: {feedback}"
                            continue
                        else:
                            user_input = (
                                f"{user_input}\n\nFeedback on plan: {raw_confirm}"
                            )
                            continue
                
                    if confirm in ("n", "no"):
                        continue

            _post_q_env = os.environ.get("UIPATH_PLAN_POST_QUESTIONS", "0").strip().lower() in (
                "1",
                "true",
                "yes",
            )
            _force_interactive = os.environ.get("UIPATH_FORCE_INTERACTIVE", "0").strip().lower() in (
                "1",
                "true",
                "yes",
            )
            if approved_plan and _post_q_env and (_force_interactive or sys.stdin.isatty()):
                from uipath_claude.query.clarifier import run_clarifier_agent

                clar_text = asyncio.run(
                    run_clarifier_agent(
                        f"{user_input}\n\n(An implementation plan was just approved.)",
                        model_name=model_name,
                        region=region,
                    )
                )
                post_qs = _parse_numbered_questions_from_clarifier(clar_text)
                if not post_qs and clar_text.strip():
                    post_qs = [clar_text.strip()[:500]]
                post_parts: list[str] = []
                for q in post_qs[:3]:
                    if not (q or "").strip():
                        continue
                    ans = Prompt.ask(q).strip()
                    if ans:
                        post_parts.append(f"Q: {q}\nA: {ans}")
                if post_parts:
                    block = "\n\n".join(post_parts)
                    clarification_prefix = (
                        f"{clarification_prefix}\n\n{block}".strip()
                        if clarification_prefix
                        else block
                    )

            runtime_context = _build_runtime_skill_context(user_input, skills)
            if approved_plan:
                runtime_context = f"{build_plan_block(approved_plan).rstrip()}\n\n{runtime_context}"
            allow_project_files = _allow_project_file_generation(user_input)
            file_intent = _is_file_generation_intent(user_input)
            if os.environ.get("UIPATH_CHAT_DEBUG_SKILLS", "0").strip().lower() in {"1", "true", "yes"}:
                traces = _debug_skill_selection(user_input, skills)
                if traces:
                    console.print("[dim]Skill selection:[/dim]")
                    for trace in traces:
                        console.print(f"  [dim]-[/dim] {trace}")
                    console.print("")
            try:
                suppress_stream_output = stream_enabled and (
                    output_mode == "quiet" or (output_mode == "auto" and file_intent)
                )
                emitted_deltas = False

                def _print_delta(delta: str) -> None:
                    nonlocal emitted_deltas
                    emitted_deltas = True
                    console.print(delta, end="")

                stream_hooks["on_delta"] = None if suppress_stream_output else _print_delta

                if stream_enabled and not suppress_stream_output:
                    console.print("[magenta]Assistant:[/magenta] ", end="")

                extra_ctx = clarification_prefix.strip() if clarification_prefix else ""
                clarification_prefix = ""
                # execute.py merges runtime_extra into skill_content for AgenticExecutor.
                # Approved plan was previously built but never passed here, so the executor
                # never saw it; include the plan block explicitly.
                runtime_extra_parts: list[str] = []
                if extra_ctx:
                    runtime_extra_parts.append(extra_ctx)
                if approved_plan:
                    runtime_extra_parts.append(build_plan_block(approved_plan).rstrip())
                runtime_extra_merged = "\n\n".join(runtime_extra_parts)

                invocation: dict[str, Any] = {
                    "messages": history + [{"role": "user", "content": user_input}],
                    "stream": bool(stream_enabled),
                    "runtime_extra": runtime_extra_merged,
                }
            
                # Check if agentic mode is enabled (has its own progress output)
                agentic_mode_on = os.environ.get("UIPATH_AGENTIC_MODE", "1").lower() in ("1", "true", "yes")
                debug_mode_on = os.environ.get("UIPATH_DEBUG_AGENT", "1").lower() in ("1", "true", "yes")
                use_spinner = not (agentic_mode_on and debug_mode_on)

                try:
                    session_store.append(
                        chat_session_id, SessionEvent(kind="user", text=user_input)
                    )
                except Exception:
                    pass

                # Always print [EXECUTING] marker for evaluation parser
                console.print("[bold yellow][EXECUTING][/bold yellow]")
                _flush_stdio()

                if use_spinner and (stream_enabled and suppress_stream_output):
                    with progress.generating("workflow"):
                        result = asyncio.run(chat_graph.ainvoke(invocation))
                elif use_spinner and (not stream_enabled and file_intent):
                    with progress.generating("workflow"):
                        result = asyncio.run(chat_graph.ainvoke(invocation))
                else:
                    result = asyncio.run(chat_graph.ainvoke(invocation))

                history[:] = list(result.get("messages") or [])
                response = str(result.get("assistant_response", ""))
                try:
                    session_store.append(
                        chat_session_id, SessionEvent(kind="assistant", text=response)
                    )
                except Exception:
                    pass
                pending_q = result.get("pending_question")
                if pending_q:
                    clarification_prefix = (
                        "The assistant asked a clarifying question. Address it in your next message:\n"
                        + str(pending_q)
                    )

                if stream_enabled and not suppress_stream_output:
                    if not emitted_deltas:
                        console.print(response, end="")
                    console.print("")
            except Exception as exc:
                progress.error("Bedrock request failed")
                console.print(
                    "Check AWS credentials, IAM permissions, model access, and AWS_REGION. "
                    f"Details: {exc}"
                )
                continue

            response_has_files = contains_file_blocks(str(response))
            suppress_output = output_mode == "quiet" or (
                output_mode == "auto" and response_has_files
            )
            if not stream_enabled:
                if not suppress_output:
                    console.print(f"[magenta]Assistant:[/magenta] {response}\n")
            elif not suppress_output and not file_intent:
                console.print("")

            if os.environ.get("UIPATH_CHAT_MATERIALIZE", "1").lower() not in (
                "0",
                "false",
                "no",
            ):
                chat_output_base = Path(
                    os.environ.get(
                        "UIPATH_CHAT_OUTPUT_DIR",
                        str(Path.cwd() / "generated" / "chat"),
                    )
                ).resolve()
                chat_root = chat_output_base / chat_session_id
                written = materialize_from_assistant_text(
                    str(response),
                    output_root=chat_root,
                    allow_project_files=allow_project_files,
                )
                if written:
                    console.print("Wrote:")
                    for path in written:
                        progress.file_written(str(path))
                    console.print("")
                
                    has_xaml = any(str(p).endswith(".xaml") for p in written)
                    auto_validate = os.environ.get("UIPATH_CHAT_AUTO_VALIDATE", "1").lower() not in ("0", "false", "no")
                
                    if has_xaml and auto_validate:
                        with progress.validating():
                            validation = validate_generated_project(chat_root)
                        if validation["success"]:
                            if validation.get("fully_validated", False):
                                progress.success("Validation passed - No errors found")
                            else:
                                progress.warning(
                                    "Structural validation passed, but Studio diagnostics were not fully run"
                                )
                            if validation.get("warnings"):
                                for warning in validation["warnings"][:5]:
                                    progress.warning(warning)
                            console.print("")
                        else:
                            progress.error(f"Validation failed - {len(validation['errors'])} error(s)")
                            for error in validation["errors"][:5]:
                                console.print(f"  [dim]-[/dim] {error}")
                            if len(validation["errors"]) > 5:
                                console.print(f"  [dim]... and {len(validation['errors']) - 5} more[/dim]")
                            console.print("")
                        
                            # Auto-fix loop
                            auto_fix = os.environ.get("UIPATH_CHAT_AUTO_FIX", "1").lower() not in ("0", "false", "no")
                            max_fix_attempts = 3
                            fix_attempt = 0
                            previous_error_fingerprint: tuple[str, ...] | None = None
                            previous_snapshot = _snapshot_files(chat_root)
                        
                            while not validation["success"] and auto_fix and fix_attempt < max_fix_attempts:
                                error_fingerprint = tuple(sorted(validation["errors"]))
                                if error_fingerprint == previous_error_fingerprint:
                                    progress.warning(
                                        "Auto-fix stopped because the same validation errors repeated."
                                    )
                                    break
                                previous_error_fingerprint = error_fingerprint
                                fix_attempt += 1
                                progress.info(f"Attempting auto-fix ({fix_attempt}/{max_fix_attempts})...")
                            
                                # Build fix prompt with error context
                                fix_prompt = f"""The generated workflow has validation errors. Please fix them:

    Errors:
    {chr(10).join('- ' + e for e in validation['errors'])}

    Please regenerate the XAML file(s) with these errors fixed."""
                            
                                history.append({"role": "user", "content": fix_prompt})
                            
                                try:
                                    with progress.generating("fix"):
                                        fix_response = asyncio.run(
                                            _get_model_response(engine, history, memory, runtime_context, stream=False)
                                        )
                                
                                    history.append({"role": "assistant", "content": str(fix_response)})
                                
                                    # Materialize the fix
                                    fix_written = materialize_from_assistant_text(
                                        str(fix_response),
                                        output_root=chat_root,
                                        allow_project_files=allow_project_files,
                                    )
                                    current_snapshot = _snapshot_files(chat_root)
                                
                                    if fix_written:
                                        for path in fix_written:
                                            progress.file_written(str(path))
                                        if current_snapshot == previous_snapshot:
                                            progress.warning(
                                                f"Fix attempt {fix_attempt} produced no file changes"
                                            )
                                            break
                                        previous_snapshot = current_snapshot
                                    
                                        # Re-validate
                                        with progress.validating():
                                            validation = validate_generated_project(chat_root)
                                    
                                        if validation["success"]:
                                            progress.success("Auto-fix successful - Validation passed")
                                            console.print("")
                                            break
                                        else:
                                            progress.warning(f"Still {len(validation['errors'])} error(s) after fix attempt {fix_attempt}")
                                            for error in validation["errors"][:3]:
                                                console.print(f"  [dim]-[/dim] {error}")
                                            console.print("")
                                    else:
                                        progress.warning(f"Fix attempt {fix_attempt} produced no file changes")
                                        break
                                except Exception as fix_exc:
                                    progress.error(f"Auto-fix attempt {fix_attempt} failed: {fix_exc}")
                                    break
                        
                            if not validation["success"]:
                                progress.error("Auto-fix exhausted. Manual intervention may be needed.")
                                console.print("")
                
                    if not allow_project_files:
                        progress.info(
                            "Generated files are artifacts. "
                            "Use a real UiPath project root for full package restore/publish."
                        )
                        console.print("")
    
    finally:
        # Cleanup: close only Studio processes opened during this session
        if track_processes and before_pids is not None:
            try:
                from uipath_claude.utils.process_tracker import finish_tracking_test, close_test_processes
                new_pids = finish_tracking_test(before_pids)
                if new_pids:
                    result = close_test_processes(force=False)
                    if result['closed']:
                        # Only show message if we actually closed something
                        console.print(f"\n[dim]Closed {len(result['closed'])} test Studio process(es)[/dim]")
            except Exception:
                pass  # Don't fail on cleanup errors


def _resolve_stream_enabled(stream_flag: bool | None) -> bool:
    """Resolve stream mode from CLI flag and environment."""
    if stream_flag is not None:
        return stream_flag
    env = os.environ.get("UIPATH_CHAT_STREAM", "1").strip().lower()
    return env not in {"0", "false", "no"}


@app.command()
def start_project(
    project_name: str = typer.Argument(..., help="Project name"),
):
    """Run full bootstrap flow (BA/SA/Dev/QA) and write artifacts to cwd."""
    from uipath_claude.query.engine_factory import create_conversation_engine_from_env

    request = f"New UiPath automation project named {project_name}"
    print(f"Starting bootstrap for: {project_name}\n")
    try:
        engine = create_conversation_engine_from_env()
    except Exception as exc:
        print("Could not initialize Bedrock model for bootstrap.")
        print(f"Details: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        result = asyncio.run(
            run_bootstrap_flow(request, engine=engine, output_root=Path.cwd())
        )
    except Exception as exc:
        print(f"Bootstrap failed: {exc}")
        raise typer.Exit(code=1) from exc

    print("Bootstrap complete. Artifact paths:")
    for key, val in sorted((result.get("paths") or {}).items()):
        print(f"  {key}: {val}")


if __name__ == "__main__":
    app()
