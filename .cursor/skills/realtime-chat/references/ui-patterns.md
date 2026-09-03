# Chat UI patterns

Load **vercel-react-best-practices** first, then only the matching `rules/` files (bundle size for markdown, waterfalls for ticket+messages fetch). After edits with `next dev` running, use **next-dev-loop**. Playwright MCP is allowed for runtime checks; do not add a project MCP server.

## Portal

| Route | Role |
|-------|------|
| `/portal/login` | Email-only login |
| `/` | Authenticated home: greeting, order chips, composer. First send creates a conversation then streams |
| `/tickets/[id]` | Existing thread (keep URL for bookmarks; same `ChatWindow`) |

Components (`web/components/portal/`):

- `chat-window.tsx` — scroll region, load history, subscribe to events
- `chat-bubble.tsx` — role alignment; markdown only for `assistant`
- `chat-composer.tsx` — textarea + send; disable while streaming
- `order-picker.tsx` — chips from `/portal/me` orders
- `typing-indicator.tsx` — shown while tokens arrive

Hook: `web/hooks/use-chat-stream.ts` — POST fetch SSE for send; `EventSource` on `/api/support/tickets/{id}/events` for passive updates (human replies). Deduplicate by message id **in current state**, and fingerprint `assistant` + `human_agent` as one family (`agent:${content}`).

**Required client behavior (do not regress):**

- Parse SSE by normalizing `\r\n` → `\n` and flushing leftover frames when the stream ends (`sse-starlette` uses CRLF).
- Commit `done.answer` into `messages` (the `message` event can be missed) **unless** that content is already on screen or the send role is `human_agent`.
- On `done`, clear `draftRef` immediately. Do not upsert leftover draft after a committed turn.
- While POST `/messages` is in flight, ignore EventSource `message` / `done` (Redis mirrors the same events).
- Keep a module-level cache keyed by `ticketId`. Next.js may re-render `/tickets/[id]` with stale `initialMessages` ~1s after POST; replacing live state makes the assistant bubble vanish until F5.
- Merge server history additively. Never `setMessages(initial)` on remount of the same ticket.

Home first send: `NewConversation` → `POST /portal/conversations` → `sessionStorage` pending text → `router.push(/tickets/{id})` → `ChatWindow` sends via POST `/messages`. `POST /portal/conversations` must reload the ticket with `get_ticket_or_404` before `ticket_to_response` (MissingGreenlet).

## Console

| Route | Role |
|-------|------|
| `/console/inbox` | Live conversation list (`last_message_at` desc), badge when `status=escalated` |
| `/console/inbox/[id]` | Split: transcript left; customer context + trace + tools right |
| `/console/escalations` | Redirect to `/console/inbox?status=escalated` |

Takeover button → `POST /tickets/{id}/takeover`. Composer uses the same messages endpoint with human role (server action or BFF fetch). Reuse `trace-timeline.tsx` and `tool-calls-table.tsx`.

## Markdown

Install `react-markdown` + `remark-gfm` only if the assistant bubble needs them. Whitelist:

`p`, `ul`, `ol`, `li`, `strong`, `em`, `code`, `a`

Skip `h1–h6`, `table`, `img`. Customer/human bubbles are plain text (`whitespace-pre-wrap`).

## Types

Fix `web/lib/api/types.ts` (`export type TicketStatus =` must exist). Add `ChatMessage`, `ChatStreamEvent`, `PortalMe`, `OrderSummary`.
