# Diagnosing selector failures

Typical errors:

- `UIPATH-UIA-001 Selector not found` — element missing or app state changed
- `UIPATH-UIA-005 Multiple elements match` — selector too broad; add an attribute or index
- `UIPATH-UIA-008 Element disabled` — wait for enabled state before interacting

## Workflow

1. Reproduce with `uip servo inspect --root <broad-selector>`
2. Compare runtime tree against the design-time selector
3. Tighten with stable attributes (`aaname`, `automationid`, `name`); avoid `idx` where possible
4. Add `uip servo screenshot --out before.png` around the failure for offline analysis
