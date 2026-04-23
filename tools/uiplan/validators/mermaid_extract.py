"""Extract fenced Mermaid diagram bodies from Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_FENCE = re.compile(
    r"^```mermaid\s*\n(?P<body>.*?)^```\s*$",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True)
class MermaidBlock:
    source_path: Path
    start_line: int
    body: str


def iter_mermaid_blocks(paths: list[Path]) -> list[MermaidBlock]:
    blocks: list[MermaidBlock] = []
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in _FENCE.finditer(text):
            body = m.group("body").rstrip("\n")
            line_no = text[: m.start()].count("\n") + 1
            blocks.append(MermaidBlock(source_path=path, start_line=line_no, body=body))
    return blocks
