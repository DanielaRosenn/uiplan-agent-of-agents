"""Scaffold checks for Python coded agents (LangGraph / generic / LlamaIndex)."""

from __future__ import annotations

import json
from pathlib import Path

from tools.uiplan.scaffold.loop_runner import run_gate_sequence
from tools.uiplan.scaffold.report import ScaffoldReport
from tools.uiplan.scaffold.adapters.base import ScaffoldAdapter


class CodedAgentScaffoldAdapter(ScaffoldAdapter):
    kind = "coded-agent"

    def run(self, *, plan_slug: str, repo_root: Path, max_loops: int) -> ScaffoldReport:
        root = repo_root.resolve()
        hints = [
            "Follow skills/skills/uipath-agents/SKILL.md for lifecycle commands.",
            "Local loop: uv sync -> uipath init (if needed) -> uipath run / pytest.",
        ]

        def skill_executor(*, iteration: int, gates: list[str]) -> dict:
            gate_results: dict[str, str] = {}
            pyproject = root / "pyproject.toml"
            if not pyproject.is_file():
                gate_results["restore"] = "fail: missing pyproject.toml"
                return {
                    "status": "failed",
                    "recoverable": False,
                    "gates": gate_results,
                    "message": "coded-agent projects expect pyproject.toml at repo root.",
                }
            text = pyproject.read_text(encoding="utf-8", errors="replace").lower()
            if "uipath" not in text:
                gate_results["restore"] = "warn: pyproject.toml has no obvious uipath dependency"
            else:
                gate_results["restore"] = "ok"

            marker = next(
                (p for p in ("langgraph.json", "agent_framework.json", "llama_index.json") if (root / p).is_file()),
                None,
            )
            if marker is None:
                gate_results["analyze"] = "fail: no agent marker json"
                return {
                    "status": "failed",
                    "recoverable": False,
                    "gates": gate_results,
                    "message": "expected one of langgraph.json, agent_framework.json, llama_index.json",
                }

            try:
                spec = json.loads((root / marker).read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                gate_results["analyze"] = f"fail: invalid json in {marker}: {e}"
                return {
                    "status": "failed",
                    "recoverable": iteration < max_loops,
                    "gates": gate_results,
                    "message": f"fix {marker} syntax",
                }

            if marker == "langgraph.json" and not isinstance(spec.get("graphs"), dict):
                gate_results["analyze"] = "fail: langgraph.json missing graphs map"
                return {
                    "status": "failed",
                    "recoverable": False,
                    "gates": gate_results,
                    "message": "langgraph.json should define graphs",
                }

            gate_results["analyze"] = "ok"
            tests_dir = root / "tests"
            if tests_dir.is_dir():
                gate_results["test"] = "ok: tests/ present"
            else:
                gate_results["test"] = "skipped: no tests/ directory"

            gate_results["pack"] = "manual: use uipath pack when ready (see uipath-agents skill)"
            return {"status": "ok", "recoverable": False, "gates": gate_results, "message": "checks passed"}

        loop_outcome = run_gate_sequence(skill_executor, max_loops)
        return ScaffoldReport(
            project_kind=self.kind,
            plan_slug=plan_slug,
            max_loops=max_loops,
            loop_outcome=loop_outcome,
            hints=hints,
        )
