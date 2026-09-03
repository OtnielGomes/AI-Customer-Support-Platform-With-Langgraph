# Customer identity (email login)

Premise: the customer is already logged into the support portal with their email. That email **is** the account key. Orders are loaded from PostgreSQL for that customer. Never create a Customer because someone typed an unknown address.

## Portal session (Next.js)

Cookie: `portal_session` (httpOnly, same-site, HMAC-signed), secret `PORTAL_SESSION_SECRET`.

Payload: customer email (normalized lower-case). Same HMAC pattern as `web/lib/auth.ts` console cookie.

Login: portal page posts to a server action → `POST /portal/session` `{ "email" }` → 200 with profile or 404.

`web/proxy.ts` (Next.js 16 proxy/middleware):

- `/console/*` requires `console_session`
- `/chat/*` and authenticated `/` require `portal_session`
- `/login` (console) and `/portal/login` (customer) stay public
- `/console/login` vs customer login must not share the same path — console stays `/login`, portal is `/portal/login`

## API header

BFF sends `X-Customer-Email` on every proxied request when the portal cookie exists.

`app/security/customer_identity.py`:

- Read header, strip, lower-case
- `select(Customer).where(func.lower(Customer.email) == email)`
- Missing header on portal routes → 401
- Unknown email → 404 (`Customer not found`)
- Type alias `CustomerDep` via `Depends`

Console routes do **not** send this header. Ticket ownership check: if the header is present, `ticket.customer_id` must equal the resolved customer.

## Portal routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/portal/session` | Validate email exists; no cookie on API (cookie is Next.js) |
| GET | `/portal/me` | Profile + orders + open conversations |
| POST | `/portal/conversations` | Create ticket: subject from first message, optional `order_id` |

After `flush`, reload with `get_ticket_or_404` (selectinload customer + resolution) before `ticket_to_response`. Accessing `ticket.customer` on a new row raises MissingGreenlet (`greenlet_spawn` / `await_only`).

`POST /tickets` must **not** insert a new Customer. Unknown email is 404. This is how orphan customers were created before.

Optional `order_id` on conversation create must belong to the authenticated customer; otherwise 409/404.

## Graph

`load_customer_context` node (after input guardrails, before supervisor) fills:

- `customer_id` (already on payload)
- `customer_public_id`, `customer_tier`, `account_status`
- `orders_summary`: list of order DTOs for that customer only — see realtime-chat SKILL.md for v2 fields (`status_label_pt`, `payment_status_label_pt`, `delivery_method_label_pt`, `estimated_delivery`, etc.)

Labels: load `data/company/company.yaml` `labels.order_status`, `labels.payment_status`, `labels.delivery_method` via shared helper (same as tools in company-architecture).

Workers receive this in the system prompt via `app/agents/prompts.py` (`IDENTITY_BLOCK`). Agent copy uses **TechStore** as the store name. Product names in context come from DB catalog (generic names only).
