# Healing agent

The healing agent automatically proposes selector fixes when production runs fail.

```bash
uip platform healing list --folder Production
uip platform healing show <suggestion-id>
uip platform healing apply <suggestion-id>
```

## When it does NOT help

- The target page changed authentication or layout entirely — re-record the workflow.
- The selector points to an iframe that moved — fix the parent selector first.
- App is in a different language/locale — use language-independent attributes.
