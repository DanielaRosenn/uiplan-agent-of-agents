# Common publish errors

| error | meaning | fix |
|---|---|---|
| `Package version already exists` | Same `version` already in feed | Bump version in `project.json`/`pyproject.toml`/`agent.json` |
| `Invalid project structure` | Missing `project.json` or `entry` | Re-scaffold with `uip rpa new` and copy code in |
| `Dependency restore failed` | Package source unreachable | Check `uip platform feed list`; configure private feeds |
| `Signature verification failed` | Signed feed and unsigned package | Sign with `uip rpa sign` or disable signing on the feed |
| `403 Forbidden` | User lacks publish role | Grant Automation Publisher role |
