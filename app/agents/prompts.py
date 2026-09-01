"""Shared identity-first and reply-style prompts for domain workers."""

from typing import Any

IDENTITY_BLOCK = """The customer is already authenticated on the support portal.
Never ask for their email or CPF. Unusable identity (not active) is Escalation,
not a chat challenge.
Use the order list below. If there is exactly one order, treat it as the subject
and never ask for ORD-xxxxx.
If there are several orders, list public_id, status, date, and amount briefly, then ask which one.
Never look up another customer's orders."""

STYLE_BLOCK = """Reply in the customer's language (default Portuguese).
Write 2 to 4 conversational sentences unless they asked for more detail.
Do not use markdown headings or tables.
Do not wrap order ids, statuses, or dates in **bold**. Write order ids as plain text (ORD-01002).
At most one short bullet list, and only when listing orders or next steps.
Do not dump tool JSON or policy yaml.
Do not claim a refund was processed unless refund_executed is true.
If you cannot finish the case and a human must take over, tell the customer
in Portuguese that you are forwarding them to a specialist who will review their problem.
Never write labels such as Escalation reason, needs_human, or other internal routing notes."""


def format_orders_summary(orders_summary: list[dict[str, Any]] | None) -> str:
    """Render a compact order list for the system prompt."""
    if not orders_summary:
        return "Known orders for this customer: none."
    lines = ["Known orders for this customer:"]
    for item in orders_summary:
        public_id = item.get("public_id", "")
        status = item.get("status_label") or item.get("status", "")
        payment = item.get("payment_status_label") or item.get("payment_status", "")
        total = item.get("total_amount", "")
        currency = item.get("currency", "BRL")
        created = (item.get("created_at") or "")[:10]
        paid_count = int(item.get("paid_payment_count") or 0)
        payment_note = payment
        if paid_count >= 2:
            payment_note = f"{payment} ({paid_count} payments)"
        line = f"- {public_id}: {status}, {payment_note}, {created}, {currency} {total}"
        items = item.get("items") or []
        if items:
            names = ", ".join(
                f"{row.get('quantity')}x {row.get('product_name')}" for row in items
            )
            eta = (item.get("estimated_delivery") or "")[:10]
            extra = f"; items: {names}"
            if eta:
                extra += f"; ETA {eta}"
            extra += " [this Ticket's Order]"
            line += extra
        lines.append(line)
    if len(orders_summary) == 1:
        lines.append("This customer has a single order. Use it without asking for the number.")
    return "\n".join(lines)


def compose_worker_prompt(
    domain_prompt: str,
    *,
    customer_name: str | None = None,
    customer_tier: str | None = None,
    account_status: str | None = None,
    orders_summary: list[dict[str, Any]] | None = None,
) -> str:
    """Concatenate domain instructions with identity and style blocks."""
    profile = []
    if customer_name:
        profile.append(f"Customer name: {customer_name}")
    if customer_tier:
        profile.append(f"Tier: {customer_tier}")
    if account_status:
        profile.append(f"Account status: {account_status}")
    profile_text = "\n".join(profile)
    return "\n\n".join(
        part
        for part in (
            domain_prompt.strip(),
            profile_text,
            format_orders_summary(orders_summary),
            IDENTITY_BLOCK,
            STYLE_BLOCK,
        )
        if part
    )
