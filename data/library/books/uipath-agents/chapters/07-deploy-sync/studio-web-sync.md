# Studio Web sync

If the team edits the agent in Studio Web in parallel:

```bash
uip codedapp pull <app-id>   # pull remote changes
# resolve conflicts in your editor
uip codedapp push            # push local changes
```

For coded agents, prefer git as the source of truth and treat Studio Web as a read-only view.
