# Claude Code Feature Relevance Matrix (UiPath Claude Code)

This matrix maps Claude Code feature families to UiPath Claude Code implementation priorities.

## Implement Now

1. **Query loop + command routing**
   - Reason: core chat UX and reliability
   - Status: implemented (REPL, slash routing, skill invocation path)

2. **Skill loading with layered sources**
   - Reason: required for UiPath + Cato + local customization
   - Status: implemented (project, user, official, templates)

3. **Slash commands**
   - Reason: discoverability and deterministic operations
   - Status: implemented and expanded (`/help`, `/status`, `/skills`, `/bootstrap`, `/analyze`, `/validate`, `/skill`)

4. **Memory injection**
   - Reason: Claude Code parity baseline and user personalization
   - Status: implemented

5. **Error transparency**
   - Reason: avoid silent fallback confusion
   - Status: implemented for Bedrock and tool setup paths

## Implement Next

1. **Tool orchestration policies**
   - Add turn-level tool limits and retries
   - Add deterministic tool-call trace output

2. **Hook governance**
   - Add per-hook timeout and allow/deny rules
   - Add safe-mode option for local shells

3. **Session snapshots**
   - Persist lightweight per-session summaries for restart continuity

4. **Structured message rendering**
   - Rich panels for tool phases and bootstrap stage transitions

## Skip / Not Relevant Right Now

1. **React/UI component parity from Claude Code**
   - UiPath Claude Code is currently terminal-first

2. **Remote IDE-specific integrations not needed for local CLI**
   - Keep codebase focused on chat + UiPath workflows

3. **Broad generic tool ecosystem**
   - Prioritize UiPath-centric tools and skills first

## UiPath-specific Additions Beyond Claude Code

1. **Official UiPath skill catalog integration**
2. **Cato template skill integration**
3. **UiPath bootstrap flow (BA -> SA -> Developer -> QA)** — L3: Bedrock turns + file artifacts under `docs/pdd|sdd|qa/` and `generated/automation/`
4. **Orchestrator and AskAI adapters**
5. **UiPath CLI validation** — `uipath studio package analyze` / `pack` via `/analyze`, `/validate`, and `cli_runner`
6. **Integration Service smoke** — `tools/uipath/integration_service.py`; override with `UIPATH_INTEGRATION_SERVICE_CHECK_CMD` when CLI verbs differ by version

