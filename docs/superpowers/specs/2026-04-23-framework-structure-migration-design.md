# Framework Structure Migration Design (Approach B, 4 Phases)

**Date:** 2026-04-23  
**Status:** Finalized 2026-04-23 — design baseline locked; **implementation merged to `main`** (see plan closure in `docs/superpowers/plans/2026-04-23-track-a-framework-structure-migration.md`).  
**Owner:** Daniela + Agent collaboration  
**Scope:** Reorganize repository root for cleaner architecture while preserving behavior and enabling safe, phased rollout.

## 1) Goal

Reshape the repository into a clearer architecture without breaking current workflows, entrypoints, and MCP/skill integrations.

## 2) Chosen direction

- Use **Approach B** (broader root reorganization), but execute with **4 strict phases** and mandatory test gates.
- Keep **Cursor-first** compatibility while retaining Claude compatibility.
- Preserve core behavior throughout migration.

## 3) Target architecture

```text
repo/
  framework/
    uipath_claude/
    mcp_server/
    tests/

  scaffold/
    template/

  ops/
    scripts/

  docs/
  skills/
  extensions/
```

### Placement rationale

- `framework/`: runtime engine and MCP internals.
- `scaffold/`: generated-project contract and templates.
- `ops/`: automation scripts and operational helpers.
- `docs/`: framework docs only.
- `skills/` + `extensions/`: stay top-level initially to reduce migration risk.

## 4) Phase plan

### Phase 1 — Baseline lock (no moves)

- Add structural contract tests.
- Add smoke harness for CLI/MCP/planning flows.
- Capture baseline outputs.

**Gate:** all baseline lanes green.  
**Checkpoint tag:** `phase-1-pass`.

### Phase 2 — Introduce new structure + dual-path compatibility

- Create target directories (`framework/`, `scaffold/`, `ops/`) without removing old paths.
- Add compatibility resolvers so old and new paths both work.

**Gate:** all baseline lanes green + dual-path assertions pass.  
**Checkpoint tag:** `phase-2-pass`.

### Phase 3 — Switch active references to new structure

- Update internal references/config/docs to prefer new paths.
- Keep fallback support for old paths.

**Gate:** all lanes green + explicit “new-path preferred” checks pass.  
**Checkpoint tag:** `phase-3-pass`.

### Phase 4 — Remove legacy path support

- Remove old path fallbacks.
- Enforce new contract in tests and doctor checks.

**Gate:** full matrix green with no legacy path reliance.  
**Checkpoint tag:** `phase-4-final`.

## 5) Test matrix (mandatory between phases)

### Lane A — Unit/integration

- Runtime tests for framework packages.

### Lane B — Structural contract

- Required path assertions for active phase.
- Resolver behavior checks (dual path where applicable).

### Lane C — CLI smoke

- Entry command availability and safe-path run.

### Lane D — MCP smoke

- Server boot, tool listing, and safe tool call.

### Lane E — Planner/lifecycle smoke

- Plan flow and safe lifecycle boundary checks.

### Lane F — Regression guard

- Command contracts unchanged.
- No stale path references.

## 6) Risk map and mitigations

### Key risks

- import/entrypoint breakage after path moves,
- MCP config path drift,
- stale graph/config paths,
- docs and scripts pointing to removed locations.

### Mitigations

- dual-path compatibility window (phases 2-3),
- strict gate progression (no partial-advance),
- phase checkpoint tags for fast rollback,
- preferred-path assertions before fallback removal.

## 7) Parallel execution with UiPlan runtime track

Running this structure migration in parallel with the UiPlan runtime restructure is valid, with coordination points.

### Track A: Structure migration (this doc)

- Owns repository topology and path contracts.

### Track B: UiPlan runtime restructure

- Owns `tools/uiplan/` + `docs/plans/_uiplan-kit/` package design and behavior.

### Coordination points (must sync)

1. **Before Phase 3:** Track B must align references to whichever path contract Track A finalizes.
2. **Before Phase 4:** Track B tests must pass against new structure with no legacy path dependency.
3. **Shared smoke suite:** one combined run before merging both tracks.

## 8) Shared safety constraints

- Existing key commands remain stable from user perspective.
- No deploy/publish side effects as part of migration work.
- No destructive file removals before phase-specific gates pass.
- Keep migration notes current for contributors.

## 9) Definition of done

- All phase gates passed in order.
- Final structure enforced by contract tests.
- Cursor-first flow verified; Claude compatibility retained.
- Combined parallel-track regression run green.
- Migration docs updated and consistent.

---

## Appendix A: Recommended initial move mapping

```text
uipath_claude/  -> framework/uipath_claude/
mcp_server/     -> framework/mcp_server/
tests/          -> framework/tests/
scripts/        -> ops/scripts/
templates/      -> scaffold/template/
```

## Appendix B: Execution policy

- No phase skipping.
- On failure: fix in phase and rerun full matrix.
- If unresolved quickly: rollback to previous checkpoint and reassess.

## Appendix C: Plan finalization (subagent-driven handoff)

When implementation resumes, use **subagent-driven-development**: one implementer per phase/task cluster, **spec** then **quality** review after each task, worktree per `using-git-worktrees`, and checkpoint suites from `docs/superpowers/plans/2026-04-23-parallel-execution-board.md`. Track A wins path-contract conflicts with Track B per the board conflict policy.
