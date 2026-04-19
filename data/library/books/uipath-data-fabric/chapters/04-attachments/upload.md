# Uploading attachments

For a field of type `attachment`:

```bash
uip df record insert Invoice --data '{"number":"INV-1"}' --attach scan=./invoice.pdf
```

Retrieve later:

```bash
uip df record get Invoice <id> --download scan=./out/invoice.pdf
```

## Limits

Attachments are stored in tenant object storage. Default per-file cap is configured per tenant; check Orchestrator settings.
