from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_MODULE_PATH = Path(__file__).resolve().parents[1] / "main.py"
_SPEC = importlib.util.spec_from_file_location("discovery_agent_main", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
run_discovery = _MODULE.run_discovery


def _load_sample_intake() -> dict:
    intake_path = (
        Path(__file__).resolve().parents[3] / "samples" / "invoice-exception" / "intake.json"
    )
    return json.loads(intake_path.read_text(encoding="utf-8"))


def test_discovery_happy_path_from_sample_intake() -> None:
    result = run_discovery(_load_sample_intake())
    normalized = result["normalizedIntake"]
    assert normalized["business_goal"]
    assert "ERP" in normalized["systems"]
    assert result["asIsFacts"]
    assert "No production deployment" in result["risks"]
    assert isinstance(normalized, dict)
