# uip feedback send

Submit a bug report or improvement suggestion to UiPath.

## Synopsis

```bash
uip feedback send --type bug|improvement --title <title> --body <markdown>
```

## Examples

```bash
uip feedback send --type bug --title 'uip rpa run hangs on Linux' --body 'Steps...'
```

## Notes

Attach diagnostics with `--include-logs` to bundle the most recent run logs.
