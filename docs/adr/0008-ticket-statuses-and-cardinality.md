# Ticket domain statuses are Open, Escalated, Resolved, Closed

A Ticket is Open while Assistant or Human Agent work continues (including after Takeover), Escalated while an Escalation waits for a Human Agent, Resolved when the case is finished, and Closed when archived. `in_progress` is runtime/UI, not glossary. The `resolutions` row is a persistence record of the answer, not a domain noun.

Status: accepted

A Customer may have many Tickets. Each Ticket binds zero or one Order.
