# uip auth login

Interactive browser-based login to UiPath Cloud.

## Synopsis

```bash
uip auth login [--tenant <name>] [--organization <slug>] [--device-code]
```

## Flags

- `--tenant` — target tenant name. Defaults to last used.
- `--organization` — organization slug from cloud.uipath.com.
- `--device-code` — fall back to device-code flow when no browser is available.

## Examples

```bash
uip auth login
uip auth login --organization acme --tenant DefaultTenant
uip auth login --device-code
```

## Common errors

- **Browser does not open**: pass `--device-code` and complete login on another machine.
- **403 after login**: user lacks access to the chosen tenant; verify in cloud.uipath.com.
- **Token expired**: re-run `uip auth login`; refresh tokens persist for ~30 days.
