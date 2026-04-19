# Inspecting faulted items

```bash
uip platform queue list-items <queue> --folder <name> --status Failed
uip platform queue item-show <item-id>
```

Key fields: `Reason`, `ProcessingException.Type`, `ProcessingException.Reason`, `RetryNumber`.
