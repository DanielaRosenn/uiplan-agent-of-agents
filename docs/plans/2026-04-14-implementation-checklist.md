# Implementation Checklist

> Quick reference for [2026-04-14-skill-first-architecture-plan.md](./2026-04-14-skill-first-architecture-plan.md)

## Phase 1: Cleanup (Do First)

```powershell
cd c:\Users\DanielaRosenstein\projects\uipath-builder-agent

# Delete empty/legacy directories
Remove-Item -Recurse -Force .worktrees -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force agent -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force archive -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force cli -ErrorAction SilentlyContinue

# Add generated to gitignore
Add-Content .gitignore "`n# Runtime output`ngenerated/"

# Commit cleanup
git add -A
git commit -m "chore: remove legacy directories and worktrees"
```

- [ ] C1: Delete `.worktrees/`
- [ ] C2: Delete `agent/`
- [ ] C3: Delete `archive/`
- [ ] C4: Delete `cli/`
- [ ] C5: Add `generated/` to `.gitignore`
- [ ] C6: Review `scripts/` - keep only essential

## Phase 2: Foundation

### Planner Router
- [ ] P1: Create `uipath_claude/query/planner_router.py`
- [ ] P2: Modify `uipath_claude/cli/app.py` - add planner check
- [ ] P3: Test planner routing with ambiguous request

### Feedback Loop
- [ ] F1: Create `uipath_claude/query/feedback_loop.py`
- [ ] F2: Integrate into chat handler
- [ ] F3: Test question detection
- [ ] F4: Add `/answer` command

### Validation Pipeline
- [ ] V1: Create `uipath_claude/validation/pipeline.py`
- [ ] V2: Integrate with artifact materialization
- [ ] V3: Add auto-fix loop (max 5)
- [ ] V4: Test with `uip rpa get-errors`

## Phase 3: Skill Tool Enhancement

- [ ] S1: Enhance `skill_tool.py` with forked execution
- [ ] S2: Add `SkillResult` dataclass
- [ ] S3: Implement question detection
- [ ] S4: Integrate into main loop

## Phase 4: Activity Discovery

- [ ] A1: Create `uipath_claude/activities/discovery.py`
- [ ] A2: Add caching
- [ ] A3: Integrate with skill tool
- [ ] A4: Add `/activity` command

## Phase 5: Graph Refactor

- [ ] G1: Create `uipath_claude/graph/state.py`
- [ ] G2: Create `uipath_claude/graph/builder.py`
- [ ] G3: Create node modules
- [ ] G4: Migrate CLI to graph execution

## Verification

Run after each phase:

```powershell
# Unit tests
pytest tests/unit -v

# Eval suite (after Phase 2+)
python scripts/eval_suite/run_first5_benchmark.py --workbook "docs/reports/eval_runs/latest.xlsx" --repo . --timeout 300
```

Target: 4/5 eval scenarios pass (80%)

## Key Files Reference

| Component | File |
|-----------|------|
| Main CLI | `uipath_claude/cli/app.py` |
| Skill Registry | `uipath_claude/skills/registry.py` |
| Skill Tool | `uipath_claude/tools/skill_tool.py` |
| Artifacts | `uipath_claude/artifacts/materialize.py` |
| Skills (submodule) | `skills/skills/` |

## Skills to Use (from UiPath/skills repo)

| Request Type | Skill |
|--------------|-------|
| Ambiguous | `uipath-planner` (MUST USE) |
| RPA workflow | `uipath-rpa` |
| Deploy to Orchestrator | `uipath-platform` |
| Python agent | `uipath-agents` |
| Flow orchestration | `uipath-maestro-flow` |
| UI automation testing | `uipath-servo` |
| Web apps | `uipath-coded-apps` |
