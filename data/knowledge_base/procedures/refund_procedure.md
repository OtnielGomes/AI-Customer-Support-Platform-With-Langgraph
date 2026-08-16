# Refund Procedure

Use only after the policy engine says the request is eligible or requires human review.

1. Verify identity (`verify_identity`).
2. Load order, items, and payments.
3. Call `check_refund_eligibility`.
4. If denied, explain the reason codes. Do not execute.
5. If `requires_human`, call `create_refund_request` (pending_approval) and escalate.
6. If eligible and below the approval threshold, create a refund request (status `requested`), original payment method only.
7. Never tell the customer the refund is processed unless status is `executed`.
