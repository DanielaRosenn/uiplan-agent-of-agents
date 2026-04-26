# UiPlan `scaffold-code` — current behavior

This note is the **baseline** for per-project-type scaffold work (see
`docs/superpowers/specs/2026-04-23-uiplan-runtime-restructure-design.md`, section 13).

## CLI entry

- Command: `uv run python -m tools.uiplan scaffold-code <plan_slug> [--max-loops N]`
- Bundle generation command: `uv run python -m tools.uiplan generate-docs <slug> [--paradigm <value>]`
- Implementation: `tools/uiplan/cli.py` (`scaffold_code`) delegates to
  `tools/uiplan/scaffold/runner.py`, which selects an adapter from
  `tools/uiplan/scaffold/registry.py` using `tools/uiplan/scaffold/project_kind.py`.

`generate-docs` now writes paradigm-aware plan/task scaffolds (descriptor files,
CLI build loop, artifact-level implementation tasks, and deploy gates) so
`scaffold-code` receives an implementation-ready `tasks.md`.

## Loop policy

- Max loops: `tools/uiplan/scaffold/loop_runner.py` (`resolve_max_loops`, optional
  `UIPLAN_MAX_LOOPS` env, `--max-loops` flag, bounds 1..25).
- Gate sequence: same module (`run_gate_sequence`) with default gates
  `restore`, `analyze`, `test`, `pack`. Adapters map each iteration to a
  structured gate result (no silent empty success for unsupported types).

## Adapters (shipped partial)

| Kind | Adapter | Behavior |
| --- | --- | --- |
| `coded-agent` | `CodedAgentScaffoldAdapter` | Validates LangGraph / agent markers + `pyproject.toml`; reports suggested `uipath` CLI follow-ups. |
| `rpa` | `RpaScaffoldAdapter` | Validates `project.json`; reports suggested `uipcli` / `uip rpa` follow-ups. |
| others | `ExplicitStubAdapter` | Single non-recoverable failure with `not_implemented` and the detected kind. |
