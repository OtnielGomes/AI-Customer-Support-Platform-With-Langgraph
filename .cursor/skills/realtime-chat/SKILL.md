---
name: realtime-chat
description: "INVOKE when changing the Customer Portal or Support Console into a live chat, adding email-based portal login, ticket_messages persistence, SSE token streaming, Redis pub/sub fan-out, human takeover, identity-first agent prompts, or chat markdown rendering. Use for portal session cookies, X-Customer-Email, POST /tickets/{id}/messages, GET /tickets/{id}/events, /console/inbox, load_customer_context, TechStore order chips with payment/delivery/fulfillment labels, prompt style that forbids decorative **bold**, duplicated chat bubbles, Escalation reason in the transcript, or a human console reply appearing twice. Do not use for Docker/bootstrap only (project-setup), generating seed rows alone (synthetic-data), or policy-engine/RAG migration (company-architecture)."
compatibility: "FastAPI, LangGraph, Redis pub/sub, Next.js App Router in web/, SSE (not WebSockets). Requires synthetic-data emails/catalog and company-architecture scoped tools."
---

# TechStore realtime chat

The portal is a **logged-in live chat**, not a ticket form. The console is a **live inbox with human takeover**. The customer is already identified by email; tools and prompts must never ask for email or invent orders they do not own.

Read [references/identity.md](references/identity.md), [references/transport.md](references/transport.md), [references/ui-patterns.md](references/ui-patterns.md), [references/prompt-style.md](references/prompt-style.md). Runtime invariants: **project-setup** `references/runtime-invariants.md`.

## Skill order

```
project-setup → synthetic-data → synthetic-policies → company-architecture → realtime-chat (this)
→ ecosystem-primer → langgraph-docs → fastapi → vercel-react-best-practices → next-dev-loop
```

## Identity-first (non-negotiable)

Graph state includes `customer_id`, `customer_public_id`, `customer_tier`, `account_status`, `orders_summary` **before** the supervisor.

### orders_summary shape (v2)

```json
{
  "public_id": "ORD-01042",
  "status": "in_transit",
  "status_label_pt": "Pedido em rota de entrega",
  "payment_status": "confirmed",
  "payment_status_label_pt": "Pagamento confirmado",
  "delivery_method": "express_sedex",
  "delivery_method_label_pt": "Rápida Sedex (até 3 dias úteis)",
  "total_amount": "2499.90",
  "created_at": "2026-08-10T14:22:00-03:00",
  "estimated_delivery": "2026-08-13T18:00:00-03:00",
  "shipping_city": "São Paulo",
  "shipping_state": "SP"
}
```

Labels from `data/company/company.yaml` `labels.*`.

| Situation | Agent must |
|-----------|------------|
| 1 order | Use that order. Never ask for `ORD-xxxxx`. |
| N orders | List: número, status PT, pagamento, entrega, valor, previsão — ask which. |
| Logistics question | May cite `shipping_city` / CEP from `get_order` (full address in console). |
| Known email | Never ask the customer to type their email. |
| Unknown email at login | Refuse — do not create Customer. |

### Portal UI order chips

`ORD-01042 · Em rota · Sedex · R$ 2.499,90` — use API labels, not raw enums.

### Agent copy

Refer to the store as **TechStore** ("sua compra na TechStore"). Use **generic product names** from order items — no real brands.

## Persistence, streaming, UI

Unchanged SSE + Redis contract. Console shows customer context: orders with PT labels, line items with catalog names, shipping city/CEP.

## What not to do

- Do not say NexaCommerce or real brand names in assistant replies.
- Do not show English enum values to customers.
- Do not regress duplicate-bubble / escalation / human-reply invariants.

## Done when

- [ ] Portal login validates email; identity-first with PT order labels
- [ ] Order chips and console context show payment + delivery + fulfillment
- [ ] Agent says TechStore; product names match DB catalog
- [ ] Each turn appears once (no duplicate bubbles)
