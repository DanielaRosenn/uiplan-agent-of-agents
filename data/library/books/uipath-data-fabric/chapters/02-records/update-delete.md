# Update and delete

```bash
uip df record update Invoice <id> --data '{"approved":true}'
uip df record delete Invoice <id>
```

Updates are partial — only supplied fields change. Pass `--replace` to replace the whole record.
