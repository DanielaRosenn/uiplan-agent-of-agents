# uip auth status

Show the current authenticated profile, organization, tenant, and token expiry.

## Synopsis

```bash
uip auth status
```

## Output

```
Profile:      default
Organization: acme
Tenant:       DefaultTenant
User:         alice@acme.com
Expires:      2026-05-19T12:00:00Z
```

## Common errors

- **Not logged in**: run `uip auth login` first.
- **Token expired**: re-run `uip auth login`.
