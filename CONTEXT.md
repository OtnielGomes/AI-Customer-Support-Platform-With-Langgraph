# TechStore Support

Customer-support product that operates inside the fictional TechStore retailer. A Customer chats about TechStore orders; some cases resolve without a Human Agent, and some must stop for validation.

## Language

### Product and merchant

**TechStore**:
The fictional Brazilian electronics retailer whose orders, payments, shipments, catalog, and commercial policies this product operates on.
_Avoid_: NexaCommerce, calling the software TechStore

**TechStore Support**:
This product: Customer Portal chat, Support Console, domain agents, and Human Agent handoff.
_Avoid_: TechStore (for the software), NexaCommerce, "the platform" as a proper name

**Customer Portal**:
The TechStore Support surface where a Customer chats on their Tickets.
_Avoid_: App, site, frontend (as the product surface name)

**Support Console**:
The TechStore Support surface where a Human Agent lists Tickets, receives Escalation, and performs Takeover.
_Avoid_: Admin, dashboard, inbox as the product name (inbox is a view)

### People

**Customer**:
A person who already has a TechStore customer record (email, orders) and may chat in TechStore Support. Portal login authenticates the email; a usable identity is an active Customer record — not a request for CPF or email in the chat.
_Avoid_: User, client, buyer, account

**Human Agent**:
A person in the Support Console who can write in the customer chat as a human.
_Avoid_: User, operator, assistant (for a person), specialist (in glossary and code; customer-facing copy may still say especialista)

### Case and voices

**Ticket**:
A support case opened by a Customer (or the Support Console) in TechStore Support. The live chat is the transcript of the Ticket, not a separate object. A Customer may have many Tickets. A Ticket has zero or one Order. The Assistant does not create another Ticket from inside a turn.
_Avoid_: Conversation, Chat (as the case), Case

**Assistant**:
The single customer-facing voice of TechStore Support on a Ticket. Supervisor and domain workers (billing, logistics, account) are internal; they are not authors in the transcript. The Assistant does not open a second Ticket to split work or to reach a Human Agent — that is Escalation or a new Ticket started in the UI. In the transcript the Assistant cites an Order by `public_id` (`ORD-xxxxx`), not by the Pedido label.
_Avoid_: Bot, AI (as the role), Billing Agent / Logistics Agent / Account Agent as visible authors

**Escalation**:
A mandatory pause: the Assistant must not resolve the Ticket. The closed list is: engine-required human (high-value, inspection, or identity not usable); delivered-but-missing; fraud; Customer demanding an exception after a lawful refusal; privacy beyond own profile; product technical assistance. A lawful refusal explained by the Assistant is not Escalation until the Customer insists on an exception. The Assistant may add Escalation; it must not execute a write the rules forbade.
_Avoid_: Takeover, intervention (as the only word), handoff (ambiguous)

**Takeover**:
A Human Agent voluntarily claims a Ticket, including when there is no Escalation.
_Avoid_: Escalation

**Open**:
Ticket status: work is ongoing (Assistant or Human Agent after Takeover).
_Avoid_: in_progress as a domain status

**Escalated**:
Ticket status: an Escalation is waiting for a Human Agent.
_Avoid_: Using Escalated for Takeover

**Resolved**:
Ticket status: the case is finished with an answer. Not a separate domain entity named Resolution.
_Avoid_: Resolution (as a glossary noun)

**Closed**:
Ticket status: archived; not the working state for a live chat.
_Avoid_: Using Closed as a synonym of Resolved

### Knowledge sources

**Fact**:
What happened in TechStore operations (Order, Payment, Shipment, catalog). Looked up; never indexed as RAG.
_Avoid_: Putting orders or payments in the knowledge base

**Policy**:
What TechStore allows: deterministic eligibility, numbers, and closed Escalation gates. Not the Assistant's opinion.
_Avoid_: Calling RAG markdown Policy in this sense; letting the Assistant invent Policy

**Document**:
How TechStore Support explains Policy and procedure to a Customer (RAG). Filenames may still contain "policy"; they remain Documents.
_Avoid_: Fact, using Document as the source of eligibility numbers

### TechStore commerce

**Withdrawal**:
The Customer's CDC cooling-off right (7 days from receipt) to undo the purchase without giving a commercial reason.
_Avoid_: Return, Refund, arrependimento as the English glossary term (customer copy may say arrependimento)

**Return**:
A commercial request to send goods back after the withdrawal window or for a stated reason (defect, wrong item, preference within the commercial window).
_Avoid_: Refund, Withdrawal, devolução as the English glossary term (customer copy may say devolução)

**Refund**:
Restitution of money. It follows a Withdrawal, a Return, or a duplicate charge — it is not the request to undo the purchase.
_Avoid_: Using Refund for Withdrawal or Return

**Payment Method**:
How the Customer paid in TechStore v1.0: PIX or credit card only.
_Avoid_: Boleto, debit card, Payment as a synonym of Payment Method

**Order**:
A TechStore purchase: items, total, shipping address, delivery deadline, and delivery method (Sedex vs standard — an attribute, not an entity). Fulfillment is the Order status (pending through delivered), not a separate noun. The Fact identifier is `public_id` (`ORD-xxxxx`). Customer-facing copy may say Pedido plus the numeric part; that label is not a second identifier and is not a lookup key.
_Avoid_: Delivery or Fulfillment as entities; Purchase, transaction; ORDER- as a prefix; treating “Pedido 01001” as the tool argument

**Payment**:
A money capture for an Order. v1.0 has one Payment per Order; two Payments exist only in a labeled duplicate-charge case.
_Avoid_: Payment Method, collapsing Payment into a field on Order

**Shipment**:
The carrier movement for an Order (zero or one). Answers “has it shipped / where is it,” not “was PIX captured.”
_Avoid_: Delivery as an entity, using Shipment for Order status

**Product**:
A sellable catalog item (generic name, no real trademark). An Order line points at a Product; the unit price is snapshotted at purchase.
_Avoid_: Brand names, SKU as the concept name, NexaPhone
