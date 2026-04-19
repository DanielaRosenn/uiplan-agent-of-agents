# Flow expression language

Used in edge `condition` and node config fields.

- Variable access: `$.invoice.amount`
- Comparison: `$.invoice.amount > 1000`
- Boolean: `$.urgent && $.invoice.amount > 1000`
- String functions: `lower($.email)`, `contains($.subject, 'urgent')`
- Null safety: `$.optional ?? 'default'`
