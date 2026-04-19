# uip df import

Bulk import records from CSV.

## Synopsis

```bash
uip df import <entity> <file.csv> [--upsert-key <field>]
```

## Examples

```bash
uip df import Invoice invoices.csv --upsert-key number
```

## Common errors

- **Header mismatch**: CSV headers must match entity field names exactly.
- **Type coercion failed**: cells must be parseable into declared field types.
