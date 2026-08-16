"""Fail if policy markdown drifts from company.yaml numbers."""

from pathlib import Path

from app.policies.loader import load_company_config

REFUND_POLICY = Path("data/knowledge_base/policies/refund_policy.md")


def test_refund_policy_documents_yaml_numbers() -> None:
    """Refund markdown must mention the canonical window, threshold, and fee."""
    company = load_company_config()
    text = REFUND_POLICY.read_text(encoding="utf-8")
    window = str(company["refund"]["standard_window_days"])
    threshold = str(int(company["refund"]["approval_threshold_brl"]))
    rate = company["refund"]["restocking_fee_rate"]
    assert window in text
    assert threshold in text
    assert "0.10" in text or "10%" in text or str(rate) in text
