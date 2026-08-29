# Assistant autonomy stops at a deterministic gate

Default: the Assistant looks up facts and may execute writes when TechStore rules allow them and do not require a human. Escalation is mandatory when the policy engine sets `requires_human` or when an explicit extra list fires (fraud, policy exception, delivered-but-missing, identity). The Assistant may Escalation extra; it must not override a blocked write. Takeover is a separate, voluntary console claim — not the same event as Escalation.

Status: accepted
