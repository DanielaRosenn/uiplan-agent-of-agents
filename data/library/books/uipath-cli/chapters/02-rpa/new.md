# uip rpa new

Scaffold a new UiPath RPA project (C# coded, XAML, or hybrid).

## Synopsis

```bash
uip rpa new <name> [--type coded|xaml|hybrid] [--target Windows|CrossPlatform]
```

## Flags

- `--type` — project type. Defaults to `coded`.
- `--target` — runtime target. Defaults to `Windows`.

## Examples

```bash
uip rpa new InvoiceBot --type coded --target CrossPlatform
uip rpa new LegacyMigration --type hybrid
```

## Common errors

- **Directory exists**: choose a new name or remove the existing folder.
- **Invalid name**: use letters, digits, dot, underscore; no spaces.
