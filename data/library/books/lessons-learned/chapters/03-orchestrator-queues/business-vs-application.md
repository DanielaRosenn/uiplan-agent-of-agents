# Business vs Application exceptions

When a queue transaction fails, classify it before calling
`system.SetTransactionStatus`:

| Kind                | Cause                                                    | Retry by Orchestrator? |
|---------------------|----------------------------------------------------------|------------------------|
| `ErrorType.Business`    | Validation failure inside the payload (Vendor missing, Amount <= 0, DueDate not parseable). The data itself is the problem. | No |
| `ErrorType.Application` | System / infrastructure failure (DB unreachable, NullReference inside the performer, transient API failure). | Yes (up to queue's max retries) |

`InvoiceQueueProcessor` uses Business for missing/invalid `Vendor` /
`Amount` / `DueDate`, and Application for any exception thrown while
inserting into `dbo.Invoices`.

Always include a human-readable `details` (the exception message or the
specific validation failure) and a short `reason` (a stable enum-ish
string the operations team can group by).
