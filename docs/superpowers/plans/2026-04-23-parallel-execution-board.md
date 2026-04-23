# Parallel Execution Board: Track A + Track B

> **Board record:** **Integrated to `main` 2026-04-23** (fast-forward `feat/parallel-a-b-impl`). Checkpoints **S1–S3** remain the regression contract for future changes. See [§ Board closure](#board-closure-2026-04-23).

## Objective

Run both approved plans in parallel while preventing cross-track breakage:

- Track A: `2026-04-23-track-a-framework-structure-migration.md`
- Track B: `2026-04-23-track-b-uiplan-runtime-restructure.md`

## Ownership lanes

| Lane | Owner | Scope |
|---|---|---|
| A1 | Migration lead | Path contracts, structure phases, compatibility windows |
| B1 | UiPlan lead | `tools/uiplan/`, `docs/uiplan/kit/`, command loop policy |
| Shared QA | Both | Sync-point tests and final regression suite |

## Sync checkpoints (hard gates)

1. **Checkpoint S1 (after A-Task2 and B-Task2)**
   - Run:
     - `uv run pytest framework/tests/migration -q`
     - `uv run pytest tools/uiplan/tests/test_template_kit.py -q`
   - Must pass before:
     - A moves to reference switching,
     - B wires loop runner to path-sensitive imports.

2. **Checkpoint S2 (before A Phase 4 fallback removal)**
   - Run:
     - `uv run pytest tools/uiplan/tests -q`
     - `uv run pytest framework/tests/mcp/test_plan_tools.py -q`
     - `uv run pytest framework/tests/migration -q`
   - Must pass with no known legacy-path dependency in Track B.

3. **Checkpoint S3 (pre-merge final suite)**
   - Run:
     - `uv run pytest tools/uiplan/tests framework/tests/migration -q`
     - `uv run pytest framework/tests/mcp/test_tool_annotations.py framework/tests/mcp/test_tool_descriptions.py framework/tests/mcp/test_plan_tools.py -q`
   - Must pass before merge.

## Branching strategy

- Branch A: `feat/structure-migration-track-a`
- Branch B: `feat/uiplan-runtime-track-b`
- Integration branch: `feat/parallel-a-b-integration`

## Conflict policy

- If both tracks touch the same file, Track A path contract wins, Track B adapts references.
- If Track B introduces path literals, replace with resolver-based path lookups before merge.
- No fallback removal commit is allowed unless S2 is green.

## Daily cadence

1. Morning: each track runs its local subset.
2. Midday: quick rebase from `main` and conflict check.
3. End-of-day: run S1/S2 criteria relevant to current phase.

## Exit criteria

- Both plans fully completed.
- All sync checkpoints green.
- Final integration branch green on S3 suite.

---

## Board closure (2026-04-23)

**Outcome:** Tracks **A** and **B** were merged onto **`main`** in one fast-forward from **`feat/parallel-a-b-impl`** (2026-04-23). Post-merge: `uv run pytest -q` **1396 passed** (9 skipped); `framework/tests/migration` + `tools/uiplan/tests` green; `submodule_guard` OK.

**This board** stays the **regression contract** for further work: re-run **S1–S3** subsets when touching path resolution, UiPlan runtime, or MCP plan surfaces.

**Subagent-driven-development** (quality shape for follow-ups):

| Stage | Requirement |
|-------|----------------|
| Per task | Fresh **implementer** context; full task text inlined (do not point subagent at plan file alone). |
| After each task | **Spec** compliance review → then **code quality** review; loop until both pass. |
| Isolation | **using-git-worktrees** before parallel mechanical work. |
| Conflict | Track A path contract wins; Track B adapts (unchanged from Conflict policy above). |

**Done means:** Exit criteria at top of this file + green S3-style suite before release promotion; `submodule_guard` on every CI run that touches `skills/`.
