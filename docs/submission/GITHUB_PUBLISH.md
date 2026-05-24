# GitHub Publish Plan (AgentHack)

## Target repository

- Intended: `danielarosenn/uiplan-agent-of-agents`
- Visibility: public

## Current blocker

Repository creation from this environment failed due GitHub Enterprise Managed User restrictions:

`Unauthorized: As an Enterprise Managed User, you cannot access this content (createRepository)`

## What is ready for push

- Submission docs under `docs/submission/`
- Real run brief: `samples/agent-of-agents/brief.enterprise-incident.real.json`
- Real viewer payload: `ui/copilotkit/current/run-events.json`
- Updated `README.md` with AgentHack quick links
- `.gitignore` updated to exclude `agents/builder-orchestrator/out/`

## Push commands (run from an account with repo-create permission)

```bash
gh repo create danielarosenn/uiplan-agent-of-agents --public --description "Agent-of-Agents: LangGraph orchestrator that turns a brief into a UiPath delivery package"
git remote add submission https://github.com/danielarosenn/uiplan-agent-of-agents.git
git push submission main
```

If the repo already exists:

```bash
git remote add submission https://github.com/danielarosenn/uiplan-agent-of-agents.git
git push submission main
```
