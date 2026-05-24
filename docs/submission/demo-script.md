# AgentHack Demo Script (2m30s)

## Runtime assets to preload

- Brief: `samples/agent-of-agents/brief.enterprise-incident.real.json`
- Real run output: `agents/builder-orchestrator/out/enterpriseincidentagentbuilder-20260524163750`
- Viewer payload: `ui/copilotkit/current/run-events.json`
- Queue/asset in Orchestrator `Shared`:
  - `Q_AGENT_OF_AGENTS_WORK`
  - `ASSET_AGENT_OF_AGENTS_POLICY`

## Timeline script

### 0:00-0:12 — Problem hook

**Screen:** split frame. Left = fragmented automation artifacts. Right = one brief JSON.

**VO:**  
"Most automation delivery still happens in disconnected handoffs. We built UiPlan to collapse that into one supervised agent run."

### 0:12-0:25 — Foundation: skills + CLI

**Screen:** `skills/skills/` folder, then terminal with `uipath --help` and `uip resource --help`.

**VO:**  
"This is built on UiPath's own skills and CLIs. We orchestrate them through a LangGraph supervisor instead of inventing a new runtime."

### 0:25-0:40 — Run the orchestrator

**Screen:** terminal in `agents/builder-orchestrator`, execute:

```bash
python -c "import json; from pathlib import Path; from main import run_orchestrator; payload=json.loads(Path('../../samples/agent-of-agents/brief.enterprise-incident.real.json').read_text(encoding='utf-8')); state=run_orchestrator(payload); print(state['runId'], state['handoff']['status'])"
```

**VO:**  
"One brief starts the full pipeline: assignment, docs, artifacts, resource checks, execution evidence, and handoff."

### 0:40-1:05 — UiPlan contract output

**Screen:** open `spec.md`, `plan.md`, `tasks.md` in sequence.

**VO:**  
"The core deliverable is UiPlan: spec, plan, and tasks. This contract is machine-readable for agents and readable for humans."

### 1:05-1:20 — Full design docs

**Screen:** open `PDD.md`, `SDD.md`, `ADD.md`.

**VO:**  
"From the same brief, the system generates formal design documents with consistent constraints and success criteria."

### 1:20-1:50 — CopilotKit 7-tab viewer

**Screen:** open `ui/copilotkit/viewer.html`, tab walkthrough:

1. UiPlan
2. Diagrams (zoom one Mermaid graph)
3. Tasks (Kanban)
4. Constraints (severity bars + skill rules + graph)
5. Execution
6. Resources
7. Docs

**VO:**  
"Every phase and artifact is observable in one viewer. The constraints tab combines skill critical rules and codebase guardrails into a severity-classified graph."

### 1:50-2:10 — Orchestrator real data

**Screen:** terminal:

```bash
uip resource queues list --folder-path "Shared" --output json
uip resource assets list --folder-path "Shared" --name "ASSET_AGENT_OF_AGENTS_POLICY" --output json
uip or jobs list --folder-path "Shared" --output json
```

Then show Orchestrator UI for `Shared` resources.

**VO:**  
"The run is grounded with real Orchestrator data: queue and asset are present, and job telemetry is queryable from the same folder."

### 2:10-2:25 — Close

**Screen:** side-by-side: brief on left, output folder tree on right.

**VO:**  
"One brief in, full delivery package out: planning, artifacts, constraints intelligence, and runtime evidence."

### 2:25-2:30 — Title card

**Screen text:**  
`UiPlan: Agent-of-Agents`  
`github.com/danielarosenn/uiplan-agent-of-agents`  
`Built for AgentHack 2026`

## Shot direction checklist

- Keep browser zoom at 110-120% for readability.
- Hold each UiPlan file at least 2 seconds.
- Spend the longest time on the Constraints tab.
- Avoid dead terminal time; pre-warm commands.
- Keep command text visible when showing Orchestrator queries.
