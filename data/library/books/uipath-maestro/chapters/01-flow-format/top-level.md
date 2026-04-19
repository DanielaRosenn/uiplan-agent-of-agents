# .flow file structure

A `.flow` is JSON with three top-level keys:

```json
{
  "metadata": { "id": "InvoiceApproval", "version": "1.0.0", "description": "..." },
  "nodes": [
    { "id": "start", "type": "start" },
    { "id": "approve", "type": "hitl", "config": { "form": "approval" } },
    { "id": "end",   "type": "end" }
  ],
  "edges": [
    { "from": "start",   "to": "approve" },
    { "from": "approve", "to": "end" }
  ]
}
```

## Rules

- Exactly one `start` node, at least one `end` node.
- All node ids are unique within the file.
- Every node except `start` must be reachable from `start`.
- Edges may carry an optional `condition` (expression in flow expression language).
