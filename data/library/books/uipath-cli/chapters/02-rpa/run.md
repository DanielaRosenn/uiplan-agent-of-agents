# uip rpa run

Execute a workflow locally for debugging.

## Synopsis

```bash
uip rpa run <entry.xaml|entry.cs> [--input '<json>'] [--watch]
```

## Examples

```bash
uip rpa run Main.xaml
uip rpa run Main.xaml --input '{"InvoiceId":"INV-42"}'
uip rpa run Main.cs --watch
```

## Common errors

- **Entry not found**: ensure the file path is relative to project root.
- **Argument mismatch**: input keys must match top-level workflow arguments.
