"""Scaffold checks for classic / modern RPA projects (project.json)."""

from __future__ import annotations

import json
from pathlib import Path

from tools.uiplan.scaffold.loop_runner import run_gate_sequence
from tools.uiplan.scaffold.report import ScaffoldReport
from tools.uiplan.scaffold.adapters.base import ScaffoldAdapter


class RpaScaffoldAdapter(ScaffoldAdapter):
    kind = "rpa"

    def run(self, *, plan_slug: str, repo_root: Path, max_loops: int) -> ScaffoldReport:
        root = repo_root.resolve()
        hints = [
            "Follow skills/skills/uipath-rpa/SKILL.md and docs/uipath-cli.md.",
            "Build loop: uipcli package restore -> analyze -> test -> pack (personal workspace only).",
        ]

        def skill_executor(*, iteration: int, gates: list[str]) -> dict:
            gate_results: dict[str, str] = {}
            pj = root / "project.json"
            if not pj.is_file():
                gate_results["restore"] = "fail: missing project.json"
                return {
                    "status": "failed",
                    "recoverable": False,
                    "gates": gate_results,
                    "message": "RPA adapter expects project.json at repo root.",
                }

            try:
                data = json.loads(pj.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                gate_results["analyze"] = f"fail: project.json invalid: {e}"
                return {
                    "status": "failed",
                    "recoverable": iteration < max_loops,
                    "gates": gate_results,
                    "message": "fix project.json",
                }

            name = data.get("name")
            ptype = data.get("projectType", "Unknown")
            if not name:
                gate_results["analyze"] = "fail: project.json missing name"
                return {
                    "status": "failed",
                    "recoverable": False,
                    "gates": gate_results,
                    "message": "add name to project.json",
                }

            gate_results["restore"] = "ok"
            gate_results["analyze"] = f"ok: projectType={ptype!r} name={name!r}"

            main = data.get("main")
            if main and (root / str(main)).is_file():
                gate_results["test"] = f"ok: entry {main} exists on disk"
            else:
                gate_results["test"] = f"warn: entry file {main!r} missing or not checked"

            gate_results["pack"] = "manual: uipcli package pack after analyze gate is green"
            return {"status": "ok", "recoverable": False, "gates": gate_results, "message": "checks passed"}

        loop_outcome = run_gate_sequence(skill_executor, max_loops)
        return ScaffoldReport(
            project_kind=self.kind,
            plan_slug=plan_slug,
            max_loops=max_loops,
            loop_outcome=loop_outcome,
            hints=hints,
        )
