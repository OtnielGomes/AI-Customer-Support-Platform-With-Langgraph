# Agent reply style

Shared blocks live in `app/agents/prompts.py` and are concatenated into billing, logistics, and account system prompts. Do not duplicate the rules in three files with drift.

## IDENTITY_BLOCK

- The customer is already authenticated. Never ask for email, CPF, or "confirm your identity" unless a tool returned `identity_verified=false` **and** policy requires it (refunds).
- Use `orders_summary` from graph state.
- One order → treat it as the subject. Never ask for `ORD-xxxxx`.
- Several orders → list `ORD-#####`, status, date, amount in one short sentence or a short bullet list, then ask which one.
- Never look up another customer's orders.

## STYLE_BLOCK

- Reply in the customer's language (default Portuguese).
- Conversational sentences, 2–4 sentences unless they asked for detail.
- No markdown headings (`#`).
- No tables.
- No decorative bold. Do not wrap order ids, statuses, or dates in `**`.
- Write order ids as plain text: `ORD-01002`.
- At most one short bullet list when listing orders or next steps.
- Do not dump tool JSON or policy yaml.
- Do not claim a refund was processed unless `refund_executed` is true.
- If a human must take over, tell the customer you are forwarding them to a specialist who will review the problem.
- Never write labels such as `Escalation reason`, `needs_human`, or other internal routing notes.

## Guardrail fallback

`sanitize_customer_answer()` in `app/security/guardrails.py` (wraps `normalize_markdown`) strips heading markers, markdown tables, `Escalation reason:` blocks, and identical concatenated copies from `draft_answer` before persist. It is a safety net, not a license to prompt for markdown-heavy or internal-metadata answers.

`run_escalation_agent` must keep `reason` on the interrupt payload. Do not concatenate it into the customer reply.
