---
id: retry-loops
title: Retry Loops
---

# Retry Loops

## When to use

- Transient failures (network, UI timing, intermittent services).

## Retry Scope

- Wrap the activities to retry; set **NumberOfRetries**, **RetryInterval**, and conditions as needed.

## Relationship to exception handling

- Prefer **Retry Scope** for bounded retries on known flaky steps.
- Use **Try Catch** / **Global Exception Handler** for failures after retries exhaust or for business logic.

