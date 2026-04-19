# Field types

| type | notes |
|---|---|
| `string` | Use `max_length` to cap |
| `text` | Long-form, no max |
| `integer` | 64-bit signed |
| `decimal` | Use `precision` and `scale` |
| `boolean` | true/false |
| `date` | ISO date |
| `datetime` | ISO 8601 with offset |
| `reference` | Foreign key; requires `target` entity name |
| `enum` | Requires `values: [...]` |
| `attachment` | File field; stored in object storage |
| `json` | Arbitrary JSON blob |
