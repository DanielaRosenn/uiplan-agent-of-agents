# uip rpa build

Compile the project and produce a `.nupkg`.

## Synopsis

```bash
uip rpa build [--output <dir>] [--configuration Release|Debug]
```

## Examples

```bash
uip rpa build
uip rpa build --output ./dist --configuration Release
```

## Common errors

- **Missing dependency**: run `uip rpa install <package>` first.
- **Selector compile error**: open the failing workflow in Studio and re-validate selectors.
