# uip case build

Build the `caseplan.json` from `sdd.md` (Solution Design Document) and `tasks.md`.

## Synopsis

```bash
uip case build [--sdd sdd.md] [--tasks tasks.md] [--out caseplan.json]
```

## Common errors

- **Unresolved task**: every task in `tasks.md` must map to a stage in the SDD.
- **Cycle in stages**: stage transitions must form a DAG.
