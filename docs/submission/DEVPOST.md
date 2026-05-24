# Devpost Submission Content

## Project Title
UiPlan: Agent-of-Agents

## Tagline
One business brief in, full UiPath delivery package out.

## Suggested Track
UiPath Maestro BPMN (Track 2) - this project demonstrates end-to-end orchestration,
human-in-the-loop checkpoints, and evidence-first execution across agent, resource,
and platform layers.

If your registered team selected a different track, keep the same content below and
map the "Track Selection" field to your registered track.

## Elevator Pitch
Most automation teams lose time in handoffs between business analysis, architecture,
development, and platform setup. UiPlan compresses that workflow into one supervised
run: submit a business brief and get a complete UiPath delivery package with planning
docs, generated artifacts, resource evidence, execution telemetry, and handoff
readiness in one place.

## What it does
UiPlan runs a LangGraph-based agent-of-agents pipeline that takes one business brief
and produces:

- UiPlan contract: `spec.md`, `plan.md`, `tasks.md`
- Formal design docs: `PDD.md`, `SDD.md`, `ADD.md`
- Build artifacts: generated flow package + execution scripts
- Resource evidence: queue/asset validation and status
- Monitoring payload: CopilotKit-compatible `run-events.json`

The pipeline stages:
1. `assign_agents`
2. `generate_design_docs`
3. `generate_uipath_artifacts`
4. `provision_resources`
5. `execute_flow`
6. `emit_ui_events`
7. `summarize_handoff`

## Business problem solved
Enterprise automation delivery is fragmented:

- Business requirements and technical design drift apart
- Runtime resources are provisioned manually and late
- Validation evidence lives in disconnected logs
- Scope changes force expensive rework across teams

UiPlan keeps all phases synchronized through a typed planning contract and a single
observable execution loop, reducing handoff loss and improving delivery reliability.

## How we built it
- Python 3.11+ orchestrator with LangGraph state machine
- UiPath CLI ecosystem:
  - `uipath` for coded agent execution
  - `uip` for resource/job queries
  - `uipcli` compatibility alignment
- Shared typed contracts in `agents/shared/agent_contracts.py`
- CopilotKit viewer (`ui/copilotkit/viewer.html`) with 7 tabs:
  UiPlan, Diagrams, Constraints, Tasks, Execution, Resources, Docs
- Constraint intelligence layer combining skill critical rules and repo constraints
- Automated narrated demo video generation with Edge TTS + MoviePy

## Real run evidence
- Run ID: `enterpriseincidentagentbuilder-20260524163750`
- Queue: `Q_AGENT_OF_AGENTS_WORK` (Shared folder)
- Asset: `ASSET_AGENT_OF_AGENTS_POLICY` (Shared folder)
- Viewer payload: `ui/copilotkit/current/run-events.json`

## Human-in-the-loop
The workflow includes explicit guardrails:
- No production deployment in assistant-driven mode
- Retry budgets and escalation gates
- Human approval checkpoints before destructive or tenant-impacting actions

## Challenges we faced
- Keeping generated plans machine-readable and human-readable at the same time
- Preserving evidence traceability across local run + platform resource state
- Balancing automation speed with governance gates
- Aligning multi-agent outputs into one coherent handoff bundle

## What we learned
- A typed `spec -> plan -> tasks` contract improves both orchestration quality and
  human review speed
- Constraint visualization dramatically improves trust and debugging
- Explicit operational evidence (resources, logs, outputs) is essential for judging
  production readiness

## What's next
- Parallelized sub-agent execution for faster run times
- Deeper Maestro-native orchestration integration
- Expanded runtime evaluators and quality gates
- Richer interactive replay of agent decisions and policy checks

## Built with
- UiPath Platform
- Python
- LangGraph
- UiPath CLI (`uipath`, `uip`, `uipcli`)
- CopilotKit viewer
- Edge TTS
- MoviePy

## Submission Links
- GitHub repo: `https://github.com/danielarosenn/uiplan-agent-of-agents`
- Demo video (upload target): YouTube/Vimeo link
- Architecture: `docs/submission/ARCHITECTURE.md`
- Written submission: `docs/submission/SUBMISSION.md`
