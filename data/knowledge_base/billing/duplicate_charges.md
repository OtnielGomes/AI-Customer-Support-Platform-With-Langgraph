# Billing — Duplicate Charges

If a customer reports a duplicate charge:

1. Verify both charges in the billing system using `list_charges`.
2. Compare invoice IDs and amounts.
3. If duplicate confirmed, initiate refund on the duplicate invoice via `request_refund`.
4. Inform the customer of the expected refund timeline (5-7 business days).

Duplicate charges often occur when a payment retry succeeds after a timeout.
