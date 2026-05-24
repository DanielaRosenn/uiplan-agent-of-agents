# UiPath Builder Agent

AgentHack 2026 submission repo for **UiPlan: Agent-of-Agents**.

## Submission Materials

Primary submission package:
- [`docs/submission/`](docs/submission/)

Supporting verification/handoff docs:
- [`docs/rebuild/`](docs/rebuild/)

Key files:
- [`docs/submission/SUBMISSION.md`](docs/submission/SUBMISSION.md)
- [`docs/submission/ARCHITECTURE.md`](docs/submission/ARCHITECTURE.md)
- [`docs/submission/DEVPOST.md`](docs/submission/DEVPOST.md)
- [`docs/submission/demo-script.md`](docs/submission/demo-script.md)
- [`docs/submission/agenthack-demo.mp4`](docs/submission/agenthack-demo.mp4)
- [`docs/submission/slide-deck.pptx`](docs/submission/slide-deck.pptx)
- [`docs/submission/SUBMISSION_CHECKLIST.md`](docs/submission/SUBMISSION_CHECKLIST.md)
- [`ui/copilotkit/current/run-events.json`](ui/copilotkit/current/run-events.json)

## Reproduce the AgentHack Run

From [`agents/builder-orchestrator/`](agents/builder-orchestrator/):

```bash
python -c "import json; from pathlib import Path; from main import run_orchestrator; payload=json.loads(Path('../../samples/agent-of-agents/brief.enterprise-incident.real.json').read_text(encoding='utf-8')); state=run_orchestrator(payload); print(state['runId'], state['handoff']['status'])"
```

## Repo Documentation Structure

- `docs/submission`: judge-facing deliverables (write-up, architecture, video, deck, checklist)
- `docs/rebuild`: execution evidence, validation, and handoff reports
- `docs/uipath-cli.md`: CLI reference
- `docs/uipath-workflows.md`: workflow/runbook guidance

## Notes

- The `skills/` submodule remains the source of truth for upstream UiPath skills.
- Keep `docs/submission` lean and handoff-ready.
- License: [`LICENSE`](LICENSE) (MIT).
