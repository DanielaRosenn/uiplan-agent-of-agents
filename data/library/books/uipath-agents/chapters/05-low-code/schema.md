# agent.json schema

Top-level fields:

```json
{
  "name": "InvoiceTriage",
  "description": "Classify and route invoices",
  "model": "uipath/llm-default",
  "system_prompt": "You are an invoice triage agent...",
  "input_schema": { "type": "object", "properties": { "invoice": { "type": "object" } }, "required": ["invoice"] },
  "output_schema": { "type": "object", "properties": { "category": { "type": "string" } }, "required": ["category"] },
  "tools": [
    { "type": "integration", "connector": "sap", "action": "get_vendor" }
  ],
  "context": [
    { "type": "data_fabric", "entity": "VendorPolicy" }
  ]
}
```

## Required

`name`, `model`, `system_prompt`, `input_schema`, `output_schema`.
