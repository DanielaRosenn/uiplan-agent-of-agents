# Pagination and ordering

```bash
uip df record query Invoice \
  --filter "amount gt 100" \
  --order-by "due_date asc" \
  --page-size 50 \
  --page-token <token>
```

Response includes `next_page_token` when more rows exist; pass it as `--page-token` to continue.
