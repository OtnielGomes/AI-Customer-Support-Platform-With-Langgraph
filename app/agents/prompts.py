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
        status = item.get("status", "")
        total = item.get("total_amount", "")
        currency = item.get("currency", "BRL")
        created = (item.get("created_at") or "")[:10]
        lines.append(f"- {public_id}: {status}, {created}, {currency} {total}")
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
