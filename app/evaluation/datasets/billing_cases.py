"""Evaluation datasets for agent quality."""

BILLING_DATASET = [
    {
        "id": "billing-001",
        "message": "I need a refund for invoice INV-1001, I was charged twice.",
        "expected_intent": "billing",
        "should_escalate": False,
        "keywords": ["refund", "INV-1001"],
    },
    {
        "id": "billing-002",
        "message": "Can you show me all my charges?",
        "expected_intent": "billing",
        "should_escalate": False,
        "keywords": ["charge", "invoice"],
    },
    {
        "id": "logistics-001",
        "message": "Where is my order ORD-5001?",
        "expected_intent": "logistics",
        "should_escalate": False,
        "keywords": ["ORD-5001", "transit"],
    },
    {
        "id": "account-001",
        "message": "I forgot my password and need to reset it.",
        "expected_intent": "account",
        "should_escalate": False,
        "keywords": ["password", "reset"],
    },
    {
        "id": "unknown-001",
        "message": "I have a vague problem with something.",
        "expected_intent": "unknown",
        "should_escalate": True,
        "keywords": [],
    },
]

ALL_DATASETS = {
    "billing": BILLING_DATASET,
}
