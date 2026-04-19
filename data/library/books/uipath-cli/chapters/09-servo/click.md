# uip servo click / type / read

Drive live desktop or browser apps.

## Synopsis

```bash
uip servo click <selector>
uip servo type <selector> <text>
uip servo read <selector>
uip servo screenshot [--out <file.png>]
```

## Examples

```bash
uip servo click '#submit'
uip servo type '[name="email"]' alice@acme.com
uip servo read '.invoice-total'
uip servo screenshot --out before.png
```

## Common errors

- **Selector not found**: confirm the app is in foreground; widen the selector or use UiExplorer.
- **Timing**: add a wait or poll before reading values that depend on async UI updates.
