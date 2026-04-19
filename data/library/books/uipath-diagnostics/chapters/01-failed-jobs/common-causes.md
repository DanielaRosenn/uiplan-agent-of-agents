# Common job failure causes

| symptom | cause | fix |
|---|---|---|
| `BusinessRuleException` | Workflow threw business rule | Inspect input data; expected user-recoverable |
| `ApplicationException` | Unhandled runtime error | Wrap with Try/Catch; log selectors and inputs |
| `Timed out` | Activity exceeded timeout | Increase timeout or add explicit wait |
| `License unavailable` | No runtime slot | Free a robot or buy capacity |
| `Asset not found` | Wrong folder or name | Verify with `uip platform asset list --folder <name>` |
