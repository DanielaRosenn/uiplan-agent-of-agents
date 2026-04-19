# uip df record

CRUD on Data Fabric records.

## Synopsis

```bash
uip df record insert <entity> --data '<json>'
uip df record query <entity> [--filter '<expr>'] [--page-size N]
uip df record update <entity> <id> --data '<json>'
uip df record delete <entity> <id>
```

## Examples

```bash
uip df record insert Invoice --data '{"number":"INV-1","amount":42.0}'
uip df record query Invoice --filter "amount gt 100"
```
