# Non-Prod Deployment Evidence

Date: 2026-05-24
Workspace: `C:/Users/DanielaRosenstein/projects/uipath-builder-agent`

## Gate execution

1. `uv sync` -> pass
2. `uv run pytest agents/shared/tests/test_contracts.py agents/builder-orchestrator/tests/test_orchestrator.py` -> pass (`12 passed`)
3. `uv run uipath init --no-agents-md-override` -> pass
4. `uv run uipath pack` -> failed
5. `uv run uipath deploy` -> blocked by same packaging failure
6. `uv run uipath pack --nolock` (in `agents/builder-orchestrator`) -> failed (before metadata fix)
7. Added `authors` to `agents/builder-orchestrator/pyproject.toml`
8. `uv run uipath pack --nolock` (in `agents/builder-orchestrator`) -> pass

## Blocker

- Packaging/deploy cannot continue because `entry-points.json` is empty:
  - Error: `No entry points found in entry-points.json. Please run 'uipath init' to generate valid entry points.`
- `uipath init` generated metadata files but detected no function entrypoints in `uipath.json`.
- Subproject packaging initially failed in `agents/builder-orchestrator`:
  - Error: `Project authors cannot be empty. Please specify authors in pyproject.toml`.
  - Resolved by adding project `authors`.
- Root pack additionally throws a terminal encoding exception on Windows after the primary failure:
  - `UnicodeEncodeError` from Rich spinner under `cp1252`.

## Additional environment check

- `python -m uipath_claude.skills.submodule_guard` still reports one pre-existing rule mismatch:
  - `CLAUDE.md references unknown skill id(s): uipath-interact`

## Conclusion

- Restore and tests passed.
- Subproject package build now passes.
- Root non-prod deploy remains blocked until root entry points are valid for packaging.
