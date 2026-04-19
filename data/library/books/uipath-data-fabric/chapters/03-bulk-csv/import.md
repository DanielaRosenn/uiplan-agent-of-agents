# Importing a CSV

```bash
uip df import Invoice invoices.csv --upsert-key number
```

## CSV requirements

- First row is the header; column names must match entity field names exactly (case-sensitive).
- Reference fields accept the target's unique key as the value.
- Booleans: `true|false`. Dates: ISO `YYYY-MM-DD`.
- Use `--dry-run` to validate without writing.

## Common errors

- **Header mismatch**: rename the column or alias via `--map csv_col=field`.
- **Type coercion failed**: invalid date or non-numeric in a numeric column.
- **Unique violation**: omit `--upsert-key` and the second insert with the same unique value will fail.
