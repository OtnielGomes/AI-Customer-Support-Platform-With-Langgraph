# Logistics — Shipping Status

Customers can track orders using order IDs (format: ORD-XXXX).

## Status Values

- `in_transit` — package is on its way
- `delivered` — package has been delivered
- `delayed` — delivery is behind schedule

Use `get_shipment_status` to retrieve carrier, ETA, and current status.

Address changes are only allowed for orders that are not yet delivered.
