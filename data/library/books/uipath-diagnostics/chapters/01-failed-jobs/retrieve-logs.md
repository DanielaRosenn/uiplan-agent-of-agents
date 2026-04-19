# Retrieving job logs

```bash
uip platform job list --folder Production --status Failed
uip platform job logs <job-id> --download ./logs/<job-id>.log
```

Logs include execution traces, robot stdout/stderr, and exception stack traces (when serialized).
