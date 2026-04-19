# Relationships

Use `reference` fields to model many-to-one. For many-to-many, create a join entity with two `reference` fields.

```json
{ "name": "InvoiceTag", "fields": [
  { "name": "invoice", "type": "reference", "target": "Invoice" },
  { "name": "tag",     "type": "reference", "target": "Tag" }
]}
```
