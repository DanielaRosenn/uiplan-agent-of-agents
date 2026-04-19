# Insert records

```bash
uip df record insert Invoice --data '{"number":"INV-1","amount":42.0,"due_date":"2026-05-01"}'
```

Returns the new record id. Reference fields accept either an id or `{"$ref":"Vendor","number":"V-7"}` to look up by unique field.
