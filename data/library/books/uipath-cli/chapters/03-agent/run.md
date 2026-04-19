# uip agent run

Run the agent locally with an input payload.

## Synopsis

```bash
uip agent run [--input '<json>'] [--trace]
```

## Examples

```bash
uip agent run --input '{"question":"reset password"}'
uip agent run --trace
```

## Common errors

- **Missing API key**: set `UIPATH_LLM_KEY` or configure via `uip auth login`.
- **Schema validation failed**: input does not match the agent’s declared input schema.
