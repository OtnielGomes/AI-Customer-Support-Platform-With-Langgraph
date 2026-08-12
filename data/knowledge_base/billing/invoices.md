# Billing — Invoice Lookup

Customers can inquire about invoice status using their invoice ID (format: INV-XXXX).

## Status Values

- `paid` — payment received
- `pending` — awaiting payment
- `overdue` — payment past due date

Use `get_invoice` with the invoice ID to retrieve details including amount, status, and date.
