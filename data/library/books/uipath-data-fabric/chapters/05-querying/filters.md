# Filter expressions

```bash
uip df record query Invoice --filter "amount gt 100 and approved eq false"
```

| operator | meaning |
|---|---|
| `eq` | equals |
| `ne` | not equals |
| `gt` `ge` `lt` `le` | numeric/date comparisons |
| `in` | value in list, e.g. `status in ('new','pending')` |
| `contains` | substring on string fields |
| `is_null` `is_not_null` | nullability |

Combine with `and`, `or`, parentheses.
