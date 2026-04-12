# Skill Picking Validation Report (Subagent-Driven Development Style)

Date: 2026-04-12  
Scope: Validate skill-selection behavior for common user intents, verify generated artifacts, and keep output folders for manual review.

## Task Breakdown

### Task 1 - Skill-picking matrix tests

Implemented:
- `tests/unit/cli/test_skill_picking_matrix.py`

Scenarios covered:
- General RPA workflow generation request -> expect `uipath-rpa-workflows`
- Coded workflow request (`.cs`, CSharp) -> expect `uipath-coded-workflows`
- PDD request -> expect `pdd-creation`
- SDD request -> expect `sdd-flow-canvas`
- Debug score trace visibility

Finding:
- Initial run exposed a bug: SDD prompts were incorrectly forced to `uipath-rpa-workflows`.
- Root cause: workflow intent forcing used broad automation tokens and overrode document intents.

Fix applied:
- Updated workflow intent detection in `uipath_claude/cli/app.py` to avoid workflow forcing for document-design intents (`pdd`, `sdd`, `document`, `architecture`, `design`) unless explicit workflow/xaml terms are present.

### Task 2 - Persistent integration artifacts

Implemented:
- `tests/integration/test_chat_skill_picking_outputs.py`

Behavior:
- Runs chat with:
  - `UIPATH_CHAT_OUTPUT_DIR=<repo>/generated/test-runs/skill-picking`
  - `UIPATH_CHAT_SESSION_ID=pytest-rpa-skill-picking`
  - `UIPATH_CHAT_DEBUG_SKILLS=1`
- Verifies:
  - file is generated
  - debug skill trace includes `uipath-rpa-workflows`

Persistent artifact path:
- `generated/test-runs/skill-picking/pytest-rpa-skill-picking/Main.xaml`

### Task 2b - Dispatcher/Performer/Long-running project bundle generation

Implemented:
- Extended `tests/integration/test_chat_skill_picking_outputs.py` with:
  - `test_chat_generates_dispatcher_performer_long_running_projects`

Behavior:
- Runs chat through CLI with a mocked file-block response that includes:
  - `dispatcher/project.json`, `dispatcher/project.uiproj`, `dispatcher/Main.xaml`
  - `performer/project.json`, `performer/project.uiproj`, `performer/Main.xaml`
  - `long-running/project.json`, `long-running/project.uiproj`, `long-running/Main.xaml`, `long-running/Main-Queue.xaml`
- Uses real template contents from `templates/dispatcher`, `templates/performer`, and `templates/long-running` to ensure generated artifacts are actual UiPath project files.
- Keeps output artifacts in persistent folders for manual Studio review.

Persistent project bundle path:
- `generated/test-runs/chat-project-bundles/pytest-project-bundles/dispatcher`
- `generated/test-runs/chat-project-bundles/pytest-project-bundles/performer`
- `generated/test-runs/chat-project-bundles/pytest-project-bundles/long-running`

### Task 3 - Full targeted suite run

Command executed:
- `pytest tests/unit/cli/test_app.py tests/unit/cli/test_skill_picking_matrix.py tests/integration/test_chat_flow.py tests/integration/test_chat_materialize.py tests/integration/test_chat_skill_picking_outputs.py`

Result:
- 31 passed, 0 failed

## Skill Picking Evaluation Summary

- Workflow intent routing works for general build requests.
- Role-like document intents (PDD/SDD) are now correctly mapped and are no longer overridden by RPA forcing.
- Debug trace output provides practical observability for selected skills and ranking.
- Generated code artifact flow is preserved and reviewable via persistent output folders.
- Multi-project generation is validated via CLI-driven chat tests and produces properly organized UiPath project folder structures.

## Changed Files

- `uipath_claude/cli/app.py`
- `tests/unit/cli/test_skill_picking_matrix.py`
- `tests/integration/test_chat_skill_picking_outputs.py`

## Notes For Manual Review

1. Open `generated/test-runs/skill-picking/pytest-rpa-skill-picking/Main.xaml`
2. Run chat with `UIPATH_CHAT_DEBUG_SKILLS=1` and compare traces across prompts:
   - Workflow request
   - PDD request
   - SDD request
3. Confirm top skill aligns with intent.
