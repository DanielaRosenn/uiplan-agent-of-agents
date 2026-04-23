"""Bootstrap flow orchestration (BA -> SA -> Developer -> QA)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from uipath_claude.agents.ba import BAAgent
from uipath_claude.agents.developer import DeveloperAgent
from uipath_claude.agents.qa import QAAgent
from uipath_claude.agents.sa import SAAgent
from uipath_claude.artifacts.writer import BootstrapArtifactWriter
from uipath_claude.query.agent_invoke import invoke_agent_llm
from uipath_claude.query.conversation import ConversationEngine
from uipath_claude.query.engine_factory import create_conversation_engine_from_env


async def run_bootstrap_flow(
    user_request: str,
    *,
    engine: ConversationEngine | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """
    Run the bootstrap flow through all agent stages.

    Writes artifacts when output_root is set (default: current working directory).

    Args:
        user_request: Initial user request
        engine: Optional Bedrock engine (defaults to env-based engine)
        output_root: Root directory for docs/ and generated/ (default cwd)

    Returns:
        Dictionary with stage outputs and artifact paths
    """
    eng = engine or create_conversation_engine_from_env()
    root = Path(output_root) if output_root is not None else Path.cwd()
    writer = BootstrapArtifactWriter(root)

    ba = BAAgent()
    pdd = await invoke_agent_llm(eng, ba.get_system_prompt(), user_request)
    pdd_path = writer.write_pdd(pdd)

    sa = SAAgent()
    sdd = await invoke_agent_llm(
        eng,
        sa.get_system_prompt(),
        f"Create SDD based on this PDD:\n\n{pdd}",
    )
    sdd_path = writer.write_sdd(sdd)

    dev = DeveloperAgent()
    code = await invoke_agent_llm(
        eng,
        dev.get_system_prompt(),
        (
            "Implement based on:\n\nPDD:\n"
            f"{pdd}\n\nSDD:\n{sdd}\n\n"
            "Produce an implementation plan, file layout, and minimal XAML "
            "outline. Default to XAML/activities for the workflow body. Only "
            "emit a `.cs` `CodedWorkflow` when (a) the user explicitly asked "
            "for a coded workflow, or (b) the implementation plan includes a "
            "one-line justification citing the rule number it satisfies in "
            "`skills/skills/uipath-rpa/references/coded-vs-xaml-guide.md`. "
            "Without that justification, treat picking coded over XAML as a "
            "planning regression and switch back to XAML."
        ),
    )
    dev_paths = writer.write_developer_artifacts(code, user_request)

    qa = QAAgent()
    validation = await invoke_agent_llm(
        eng,
        qa.get_system_prompt(),
        f"Validate this implementation plan and scaffold:\n\n{code}",
    )
    qa_path = writer.write_qa(validation)

    return {
        "pdd": pdd,
        "sdd": sdd,
        "code": code,
        "validation": validation,
        "paths": {
            "pdd": str(pdd_path),
            "sdd": str(sdd_path),
            "qa": str(qa_path),
            **dev_paths,
        },
    }
