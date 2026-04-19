# Escalation

Use a `branch` after `hitl` keyed on the timeout flag:

```json
{"from":"approve","to":"escalate","condition":"$.approve.timed_out == true"},
{"from":"approve","to":"book",     "condition":"$.approve.approved == true"},
{"from":"approve","to":"reject",   "condition":"$.approve.approved == false"}
```

`escalate` is typically another `hitl` with a different assignee plus a notification side effect.
