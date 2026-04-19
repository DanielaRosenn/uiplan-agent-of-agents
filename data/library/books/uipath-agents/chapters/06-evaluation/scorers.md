# Built-in scorers

- `exact:<path>` — exact match on JSONPath in output
- `contains:<path>:<substr>` — substring match
- `regex:<path>:<pattern>` — regex match
- `llm-judge:<criteria>` — model-graded boolean
- `latency_ms:<max>` — latency budget
- `cost_usd:<max>` — cost budget

Multiple scorers per case are AND-ed; the case passes only if all pass.
