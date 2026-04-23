"""Stub skill executor for tests and offline CLI wiring."""


def noop_skill_executor(iteration: int, gates: list[str]) -> dict:
    """Always succeeds; ignores ``iteration`` and ``gates``."""
    return {"status": "ok", "recoverable": True, "iteration": iteration, "gates": gates}
