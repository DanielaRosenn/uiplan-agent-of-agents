"""Optional Mermaid CLI (mmdc) validation."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from tools.uiplan.validators.mermaid_extract import MermaidBlock, iter_mermaid_blocks


def mmdc_on_path() -> str | None:
    return shutil.which("mmdc")


def validate_mermaid_with_mmdc(paths: list[Path]) -> list[str]:
    """
    Run ``mmdc`` on each extracted block. Requires Node and ``@mermaid-js/mermaid-cli``.

    Returns a list of human-readable error lines (empty if all pass).
    """
    mmdc = mmdc_on_path()
    if mmdc is None:
        return ["mmdc not found on PATH; install with: npm install -g @mermaid-js/mermaid-cli"]

    issues: list[str] = []
    blocks = iter_mermaid_blocks([p.resolve() for p in paths])
    for block in blocks:
        err = _run_one(mmdc, block)
        if err:
            issues.append(err)
    return issues


def _run_one(mmdc: str, block: MermaidBlock) -> str | None:
    with tempfile.TemporaryDirectory(prefix="uiplan-mmdc-") as tmp:
        src = Path(tmp) / "in.mmd"
        out = Path(tmp) / "out.svg"
        src.write_text(block.body + "\n", encoding="utf-8")
        proc = subprocess.run(
            [mmdc, "-i", str(src), "-o", str(out)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode == 0 and out.is_file():
            return None
        detail = (proc.stderr or proc.stdout or "").strip()
        rel = block.source_path.as_posix()
        tail = f": {detail}" if detail else ""
        return f"{rel}:{block.start_line}: mmdc failed{tail}"
