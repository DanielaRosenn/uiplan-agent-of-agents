# uip platform asset

Manage assets (text, integer, bool, credential) in a folder.

## Synopsis

```bash
uip platform asset list --folder <name>
uip platform asset set <name> --folder <name> --value <value> [--type text|int|bool|credential]
uip platform asset get <name> --folder <name>
uip platform asset delete <name> --folder <name>
```

## Examples

```bash
uip platform asset set ApiBaseUrl --folder Shared --value https://api.acme.com
uip platform asset set DbCreds --folder Shared --type credential --value 'user:pass'
```
