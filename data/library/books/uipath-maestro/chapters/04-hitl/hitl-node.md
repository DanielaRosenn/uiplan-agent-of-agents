# hitl node

```json
{
  "id": "approve",
  "type": "hitl",
  "config": {
    "form": {
      "title": "Approve invoice",
      "fields": [
        { "name": "approved", "type": "boolean", "label": "Approve?" },
        { "name": "comment",  "type": "string",  "label": "Comment", "required": false }
      ]
    },
    "assignee": "$.approver_email",
    "timeout": "PT24H",
    "on_timeout": "escalate"
  }
}
```

## Outputs

Downstream nodes see `$.approve.approved` and `$.approve.comment`.
