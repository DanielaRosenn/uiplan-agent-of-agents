"""Write PDD, SDD, QA, and developer scaffold files."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (s[:max_len] or "automation").rstrip("-")


class BootstrapArtifactWriter:
    """Writes bootstrap artifacts under output_root."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = Path(output_root).resolve()
        self.stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    def write_pdd(self, content: str) -> Path:
        path = self.output_root / "docs" / "pdd" / f"{self.stamp}-pdd.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_sdd(self, content: str) -> Path:
        path = self.output_root / "docs" / "sdd" / f"{self.stamp}-sdd.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_qa(self, content: str) -> Path:
        path = self.output_root / "docs" / "qa" / f"{self.stamp}-validation.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_developer_artifacts(
        self,
        llm_output: str,
        user_request: str,
    ) -> dict[str, str]:
        """Write implementation plan + minimal UiPath project scaffold."""
        base = self.output_root / "generated" / "automation" / f"{self.stamp}-{_slug(user_request)}"
        base.mkdir(parents=True, exist_ok=True)

        plan_path = base / "IMPLEMENTATION_PLAN.md"
        plan_path.write_text(llm_output, encoding="utf-8")

        project_name = _slug(user_request).replace("-", " ").title() or "GeneratedProcess"
        project_json: dict[str, Any] = {
            "name": project_name[:64],
            "projectType": "Process",
            "main": "Main.xaml",
            "dependencies": {},
        }
        pj = base / "project.json"
        pj.write_text(json.dumps(project_json, indent=2), encoding="utf-8")

        main_xaml = base / "Main.xaml"
        main_xaml.write_text(_minimal_main_xaml(), encoding="utf-8")

        return {
            "implementation_plan": str(plan_path),
            "project_dir": str(base),
            "project_json": str(pj),
            "main_xaml": str(main_xaml),
        }


def _minimal_main_xaml() -> str:
    """Minimal Sequence workflow for Studio compatibility (outline)."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main"
 xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Main Sequence">
    <WriteLine Text="Generated scaffold — replace with real activities in UiPath Studio." />
  </Sequence>
</Activity>
"""
