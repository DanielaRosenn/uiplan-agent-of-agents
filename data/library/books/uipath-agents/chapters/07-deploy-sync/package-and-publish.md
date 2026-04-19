# Package and publish

Coded agents:

```bash
uip agent deploy --folder Production --version 1.2.0
```

This builds a `.nupkg`, uploads to Orchestrator under the chosen folder, and registers it as a runnable agent.

Low-code agents are auto-deployed when you publish from Agent Builder; CLI deploy uploads the local `agent.json`.
