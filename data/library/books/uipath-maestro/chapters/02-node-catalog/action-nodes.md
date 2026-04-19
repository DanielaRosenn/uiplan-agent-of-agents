# Action nodes

| type | purpose | key config |
|---|---|---|
| `llm` | Call an LLM | `model`, `prompt`, `output_schema` |
| `tool_call` | Call a registered tool | `tool`, `args` |
| `integration` | Integration Service action | `connector`, `action`, `args` |
| `process` | Trigger Orchestrator process | `process`, `folder`, `input` |
| `flow` | Invoke a sub-flow | `flow`, `input` |
| `data_fabric` | Read/write Data Fabric | `entity`, `op`, `args` |
| `hitl` | Human-in-the-loop | `form`, `assignee`, `timeout` |
| `transform` | JSON transform via expression | `output` |

## LLM example

```json
{
  "id": "classify",
  "type": "llm",
  "config": {
    "model": "uipath/llm-default",
    "prompt": "Classify: {{$.subject}} into billing|support|sales.",
    "output_schema": {"type": "object", "properties": {"category": {"type": "string"}}}
  }
}
```
