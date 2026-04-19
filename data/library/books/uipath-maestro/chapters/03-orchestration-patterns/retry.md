# Retry pattern

Most action nodes accept a `retry` block:

```json
{
  "id": "call_api",
  "type": "integration",
  "config": { "connector": "sap", "action": "get_vendor" },
  "retry": { "max_attempts": 3, "backoff_ms": 1000, "on": ["timeout", "5xx"] }
}
```
