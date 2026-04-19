# Retry policy

Queue retry behavior is set on the queue:

- `MaxNumberOfRetries` — default 1; raise for transient errors only.
- `AcceptAutomaticallyRetry` — must be true for retries to happen.
- Application exceptions retry; business exceptions do not.

Requeue manually:

```bash
uip platform queue requeue <item-id>
```
