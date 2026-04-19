# uip agent deploy

Package and publish the agent to UiPath Cloud.

## Synopsis

```bash
uip agent deploy [--folder <name>] [--version <semver>]
```

## Examples

```bash
uip agent deploy --folder Production --version 1.2.0
```

## Common errors

- **Folder not found**: create it via `uip platform folder create` or in Orchestrator.
- **Version conflict**: bump the version in `pyproject.toml` or `agent.json`.
