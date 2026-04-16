"""/knowledge — print cross-skill knowledge index JSON."""
from __future__ import annotations

import json
from pathlib import Path

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.skills.knowledge_index import build_index


def register_knowledge_command(registry: CommandRegistry, project_root: Path) -> None:
    def handle_knowledge(*_args: str) -> str:
        idx = build_index(project_root.resolve())
        return json.dumps(idx, indent=2)

    registry.register("knowledge", "Show authored skills + top lessons index", handle_knowledge)
