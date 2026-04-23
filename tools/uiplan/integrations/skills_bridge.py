"""Bridge between UiPlan scaffold loops and specialist skills (stub)."""


def noop_skill_executor(iteration: int, gates: list[str]) -> dict:
    """Stub executor that always reports a successful gate run (for tests and dry runs)."""
    return {"status": "ok", "recoverable": True}
