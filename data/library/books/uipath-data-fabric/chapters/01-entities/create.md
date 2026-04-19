# Creating a Data Fabric entity

Define the schema as JSON, then create:

```json
{
  "name": "Invoice",
  "display_name": "Invoice",
  "fields": [
    { "name": "number",   "type": "string",   "required": true, "unique": true },
    { "name": "amount",   "type": "decimal",  "required": true },
    { "name": "vendor",   "type": "reference", "target": "Vendor" },
    { "name": "approved", "type": "boolean",  "default": false },
    { "name": "due_date", "type": "date" }
  ]
}
```

```bash
uip df entity create Invoice --schema invoice.schema.json
```
