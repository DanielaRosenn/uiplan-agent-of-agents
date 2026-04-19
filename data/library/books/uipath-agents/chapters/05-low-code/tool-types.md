# Tool types in agent.json

| type | use |
|---|---|
| `integration` | Call an Integration Service connector action |
| `data_fabric` | Read/write a Data Fabric entity |
| `process` | Trigger an Orchestrator process |
| `flow` | Invoke a Maestro Flow |
| `http` | Generic HTTP call |
| `python` | Execute a registered Python tool function |

Each tool entry must include the keys required by its type (e.g., `connector`+`action` for `integration`).
