# uip agent new

Scaffold a coded or low-code agent project.

## Synopsis

```bash
uip agent new <name> [--framework langgraph|llamaindex|openai|low-code]
```

## Examples

```bash
uip agent new TriageAgent --framework langgraph
uip agent new SupportBot --framework low-code
```

## Notes

Low-code agents produce an `agent.json`; coded agents produce a Python project with `pyproject.toml`.
