# Control nodes

| type | purpose |
|---|---|
| `start` | Entry point. No inputs. |
| `end` | Terminal. Multiple allowed. |
| `branch` | Routes based on edge `condition`. |
| `loop` | Iterates over `$.items`; emits `$.item` per iteration. |
| `parallel` | Fan-out to N branches; joins on `parallel_join`. |
| `parallel_join` | Wait for all matching `parallel` branches. |

## Branch example

```json
{ "id": "route", "type": "branch" }
```

With edges:

```json
{ "from": "route", "to": "approve", "condition": "$.amount > 1000" },
{ "from": "route", "to": "auto_pay", "condition": "$.amount <= 1000" }
```
