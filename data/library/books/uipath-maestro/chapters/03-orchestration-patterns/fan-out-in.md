# Fan-out / fan-in

Use `parallel` + `parallel_join` to run independent work concurrently.

```json
{"id":"split","type":"parallel"},
{"id":"enrich_a","type":"integration","config":{...}},
{"id":"enrich_b","type":"integration","config":{...}},
{"id":"join","type":"parallel_join","config":{"branches":["enrich_a","enrich_b"]}}
```

Outputs are available as `$.enrich_a` and `$.enrich_b` after `join`.
