# UiPlan Runtime Restructure Design

**Date:** 2026-04-23  
**Status:** Finalized 2026-04-23 — design baseline locked; **implementation merged to `main`** (see plan closure in `docs/superpowers/plans/2026-04-23-track-b-uiplan-runtime-restructure.md`).  
**Owner:** Daniela + Agent collaboration  
**Scope:** Reshape `_uiplan` into a spec-kit style package with explicit docs generation and scaffold execution phases, while preserving Cursor-first and Claude-compatible best practices.

## 1) Problem and intent

Legacy `docs/plans/_uiplan/` templates are superseded by the kit under `docs/uiplan/kit/` for full planning-to-build execution.  
The target is a first-class UiPlan package that:

- mirrors superpowers/spec-kit quality for documentation and structure,
- embeds UiPath-specific planning intelligence (PDD/SDD, skills, Maestro subflow guidance),
- and executes build/validation loops through existing skills and CLI gates.

## 2) Decisions locked in this design

1. **Architecture model:** Hybrid split
   - Runtime package under `tools/uiplan/`.
   - Human-facing kit under `docs/uiplan/kit/` (see `docs/uiplan/README.md`).
2. **Command model:** Explicit two-step (Option A)
   - `uiplan generate-docs`
   - `uiplan scaffold-code`
3. **Execution policy:** Skill-driven bounded auto-fix loop
   - Use specialist skills for project-type execution.
   - Enforce restore/analyze/test/pack gates.
   - Retry recoverable failures only, with configurable max loops.

## 3) Target structure

```text
tools/
  uiplan/
    cli.py
    generators/
      spec_generator.py
      plan_generator.py
      tasks_generator.py
    scaffold/
      rpa_adapter.py
      coded_agent_adapter.py
      maestro_flow_adapter.py
      mixed_adapter.py
    validators/
      mermaid_validator.py
      lineage_validator.py
      gate_validator.py
    integrations/
      mcp_bridge.py
      skills_bridge.py
      maestro_subflow_bridge.py
    tests/

docs/
  uiplan/
    README.md
    HOW_TO_USE.md
    kit/
      README.md
      _spec-template.md
      _plan-template.md
      _tasks-template.md
      _diagram-patterns.md
  plans/
    README.md
    constitution.md
    <slug folders> / single-file plans
```

## 4) Command behavior

### `uiplan generate-docs`

Produces a complete planning bundle:

- Spec, plan, and tasks documents from `docs/uiplan/kit/` templates.
- Required Mermaid architecture/flow diagrams.
- Embedded references to:
  - existing project PDD/SDD (when present),
  - relevant skill hints,
  - Maestro subflow planning guidance.
- Lineage metadata that tracks source document state at generation time.

### Human approval gate (required)

`scaffold-code` is blocked until docs are accepted.  
Minimum gate checks:

- no unresolved placeholders,
- at least one valid Mermaid block,
- tasks are actionable and path-specific,
- assumptions/open questions are explicit.

### `uiplan scaffold-code`

Consumes approved docs and prepares initial code/project skeleton via specialist skills and adapters:

- routes by project type (`rpa`, `coded-agent`, `maestro-flow`, `mixed`),
- writes scaffold report (created, skipped, manual follow-ups),
- never deploys or publishes.

## 5) Skill-driven build/validate loop

The loop is delegated to existing skills (no duplicated business logic):

- `uipath-rpa` for RPA/coded workflow execution,
- `uipath-agents` for coded-agent execution,
- `uipath-maestro-flow` for flow/subflow execution.

UiPlan wraps these skills with common mandatory gates:

1. restore
2. analyze (blocking)
3. test (blocking)
4. pack/build

On recoverable failure:

- apply bounded fix attempt,
- rerun gates,
- repeat until pass or loop limit reached.

On non-recoverable failure:

- fail immediately with structured report.

## 6) Configurable loop count

Loop count must be configurable (user requirement).

### Proposed configuration

- CLI flag: `--max-loops <int>`
- Environment fallback: `UIPLAN_MAX_LOOPS`
- Default: `5`
- Allowed range: `1..25`

### Rules

- If both flag and env var are set, CLI flag wins.
- Invalid values fail fast with clear error.
- Effective value is always printed in run summary.

## 7) Failure classification

### Recoverable (eligible for retry loop)

- analyzer/test errors that can be fixed by generated code or file adjustments,
- template/render mismatches with deterministic fixes,
- non-destructive config/path mistakes.

### Non-recoverable (immediate fail)

- missing authentication/prerequisite tooling,
- CLI version mismatch violating policy,
- hard governance/policy gate violations,
- missing explicit approvals for guarded operations,
- ambiguous project type that cannot be inferred safely.

## 8) Maestro subflow integration

The subflow planning reference at `.cursor/skills/uipath-maestro-flow/references/plugins/subflow/planning.md` is embedded as a planning rule in:

- `_diagram-patterns.md` (diagram semantics),
- project-type generation rules (`maestro-flow` adapter),
- validation checks ensuring subflow boundaries are explicit.

## 9) PDD/SDD and skill embedding

UiPlan integrates with existing assets before build:

- pulls `docs/PDD.md` / `docs/SDD.md` when available,
- links formal lifecycle context from `docs/PDD_LIFECYCLE.md`,
- includes skill-aware sections in generated plan artifacts so build steps remain aligned with existing toolchain.

## 10) Migration from current `_uiplan`

Completed path:

1. `tools/uiplan/` runtime package (Typer CLI, loop runner).
2. Kit lives at `docs/uiplan/kit/` with `_diagram-patterns.md` and Pro Standard templates.
3. `docs/plans/_uiplan/README.md` stub points to the new kit; duplicate templates under `docs/plans/_uiplan/` were removed.
4. `.cursor/skills/uiplan/SKILL.md` links `docs/uiplan/README.md` as the canonical human entry.

## 13) Phase 4 closure — generate-docs MVP vs backlog

**Shipped (MVP):**

- `tools/uiplan/generators/docs_bundle.py` — copy kit templates to `spec.md` / `plan.md` / `tasks.md` with baseline placeholder substitution.
- `tools/uiplan/validators/visual_density.py` — minimum Mermaid counts + Pro Standard heuristics (`classDef`, `linkStyle` on flowcharts).
- `uv run python -m tools.uiplan generate-docs <slug>` wired with `--out`, `--kit`, `--strict`.

**Backlog (design §3 parity):**

- Per-project-type adapters under `tools/uiplan/scaffold/` beyond the current stub loop.
- `mmdc` syntax validation when CLI available.
- Rich MCP bridges (`integrations/mcp_bridge.py` patterns) as described in earlier sections of this doc.

## 11) Test strategy

### Unit tests

- template rendering and placeholder checks,
- mermaid/style validation,
- lineage and approval gate logic,
- loop count parsing and bounds.

### Integration tests

- `generate-docs` output correctness by project type,
- `scaffold-code` routing to correct adapter/skill,
- loop execution with recoverable and non-recoverable failure paths.

### Regression/smoke

- existing planner and MCP flows remain intact,
- skill references and docs links valid,
- Cursor-first usage remains smooth; Claude remains compatible.

## 12) Safety and rollout

- Phase migration with per-phase test gates.
- Explicit rollback checkpoints.
- No destructive deploy/publish in this package scope.

---

## Appendix A: Example execution summary output

```text
uiplan scaffold-code --max-loops 7
project_type: rpa
effective_max_loops: 7
loop: 1 restore=ok analyze=fail test=skipped pack=skipped
loop: 2 restore=ok analyze=ok test=fail pack=skipped
loop: 3 restore=ok analyze=ok test=ok pack=ok
status: success
```

## Appendix B: Notes from prior planning lineage

This design continues the earlier superpowers-style planning work captured in transcript `cc66b440-fb95-467a-b009-2c45c3082ad3`, while shifting `_uiplan` into a cleaner runtime/docs split with stronger execution gating.

## Appendix C: Plan finalization (subagent-driven handoff)

When implementation resumes, use **subagent-driven-development** (or **executing-plans** for a parallel session): one fresh implementer per plan task, **spec compliance review** then **code quality review** after each task, worktree isolation per `using-git-worktrees`, and verification gates from `docs/superpowers/plans/2026-04-23-parallel-execution-board.md`. Do not treat unchecked items in the implementation plan as authoritative for repo state until re-audited against the tree.
