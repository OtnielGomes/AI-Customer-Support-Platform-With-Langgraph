"""Permission scope constants."""

READ = "read"
WRITE = "write"
BILLING_READ = "billing:read"
BILLING_WRITE = "billing:write"
LOGISTICS_READ = "logistics:read"
LOGISTICS_WRITE = "logistics:write"
ACCOUNT_READ = "account:read"
ACCOUNT_WRITE = "account:write"

TOOL_PERMISSIONS: dict[str, list[str]] = {
    "get_invoice": [BILLING_READ, READ],
    "list_charges": [BILLING_READ, READ],
    "request_refund": [BILLING_WRITE, WRITE],
    "search_knowledge_base": [READ],
    "get_shipment_status": [LOGISTICS_READ, READ],
    "update_delivery_address": [LOGISTICS_WRITE, WRITE],
    "get_account_profile": [ACCOUNT_READ, READ],
    "reset_account_password": [ACCOUNT_WRITE, WRITE],
}
