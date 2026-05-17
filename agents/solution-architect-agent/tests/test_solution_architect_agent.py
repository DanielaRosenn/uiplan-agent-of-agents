from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_MODULE_PATH = Path(__file__).resolve().parents[1] / "main.py"
_SPEC = importlib.util.spec_from_file_location("solution_architect_main", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
run_solution_architect = _MODULE.run_solution_architect


def _load_sample_intake() -> dict:
    intake_path = (
        Path(__file__).resolve().parents[3] / "samples" / "invoice-exception" / "intake.json"
    )
    return json.loads(intake_path.read_text(encoding="utf-8"))


def test_solution_architect_happy_path_from_sample_intake() -> None:
    plan = run_solution_architect(_load_sample_intake())
    assert "Coded Agent" in plan.uipath_surfaces
    assert "Action Center" in plan.uipath_surfaces
    assert plan.workflow_catalog
    assert "TO-BE" in plan.title
