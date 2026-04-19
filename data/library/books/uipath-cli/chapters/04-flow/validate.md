# uip flow validate

Validate a `.flow` for schema, edge integrity, and unreachable nodes.

## Synopsis

```bash
uip flow validate <file.flow>
```

## Common errors

- **Unreachable node**: every node must be reachable from `Start`.
- **Dangling edge**: edge target id missing.
- **Type mismatch**: node output type does not match downstream input.
