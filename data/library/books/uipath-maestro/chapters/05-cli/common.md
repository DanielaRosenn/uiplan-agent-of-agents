# Maestro CLI

See book `uipath-cli`, chapter `flow` for full reference.

```bash
uip flow new InvoiceApproval
uip flow validate InvoiceApproval.flow
uip flow run InvoiceApproval.flow --input '{"amount":1200}'
```

## Tips

- Always `validate` before `run`; catches dangling edges and unreachable nodes early.
- Use `--input` with realistic payloads when iterating; flows fail fast on schema mismatches.
