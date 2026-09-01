"""Permission scope constants."""

READ = "read"
WRITE = "write"
BILLING_READ = "billing:read"
BILLING_WRITE = "billing:write"
LOGISTICS_READ = "logistics:read"
LOGISTICS_WRITE = "logistics:write"
ACCOUNT_READ = "account:read"

TOOL_PERMISSIONS: dict[str, list[str]] = {
    "get_order": [BILLING_READ, LOGISTICS_READ, READ],
    "get_order_items": [BILLING_READ, LOGISTICS_READ, READ],
    "get_payments": [BILLING_READ, READ],
    "get_payment_status": [BILLING_READ, READ],
    "check_refund_eligibility": [BILLING_READ, READ],
    "create_refund_request": [BILLING_WRITE, WRITE],
    "search_knowledge_base": [READ],
    "get_shipment": [LOGISTICS_READ, READ],
    "get_shipping_status": [LOGISTICS_READ, READ],
    "get_return_status": [LOGISTICS_READ, READ],
    "create_return_request": [LOGISTICS_WRITE, WRITE],
    "cancel_order": [LOGISTICS_WRITE, WRITE],
    "get_customer": [ACCOUNT_READ, READ],
    "verify_identity": [ACCOUNT_READ, READ],
    "evaluate_escalation": [READ],
}
