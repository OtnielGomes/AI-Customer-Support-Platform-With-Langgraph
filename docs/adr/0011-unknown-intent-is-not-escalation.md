# Unknown intent is not Escalation; Order Facts default to logistics

The supervisor does not pause for a Human Agent because intent is `unknown` or confidence is below threshold. A known domain (billing, logistics, account) still goes to that worker even when confidence is low. Only `unknown` defaults to logistics, which owns Order Facts (items, status, dates, generic help with the Order). The customer-facing specialist sentence is Escalation copy only — a missed lookup stays in-thread.

Status: accepted

Considered Options: unknown → Escalation (catalog theater; premature pause); all low-confidence → logistics (sends a shaky refund to shipping); a fourth Order-facts worker (no new domain term).
