import pytest

from tools.uiplan.integrations.skills_bridge import noop_skill_executor
from tools.uiplan.scaffold.loop_runner import (
    resolve_max_loops,
    run_gate_sequence,
)


def test_cli_flag_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UIPLAN_MAX_LOOPS", "9")
    assert resolve_max_loops(4) == 4


def test_bounds_reject() -> None:
    with pytest.raises(ValueError, match="max_loops must be between"):
        resolve_max_loops(0)
    with pytest.raises(ValueError, match="max_loops must be between"):
        resolve_max_loops(26)
    with pytest.raises(ValueError, match="UIPLAN_MAX_LOOPS must be an integer"):
        resolve_max_loops(None, "not-a-number")
    with pytest.raises(ValueError, match="UIPLAN_MAX_LOOPS must be between"):
        resolve_max_loops(None, "0")


def test_run_gate_sequence_succeeds_first_iteration() -> None:
    out = run_gate_sequence(noop_skill_executor, max_loops=3)
    assert out["status"] == "ok"
    assert out["iteration"] == 1
