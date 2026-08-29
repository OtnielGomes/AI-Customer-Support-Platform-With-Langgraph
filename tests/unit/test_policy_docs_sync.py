"""Fail if Documents drift from the TechStore world model."""

from pathlib import Path

from app.policies.loader import load_company_config

KB_ROOT = Path("data/knowledge_base")
REFUND_POLICY = KB_ROOT / "policies" / "refund_policy.md"
PAYMENT_POLICY = KB_ROOT / "policies" / "payment_policy.md"
OVERVIEW = KB_ROOT / "company" / "company_overview.md"


def test_company_world_model_is_techstore() -> None:
    """Loaded company config names the merchant TechStore with v1.0 Payment Methods."""
    company = load_company_config()
    assert company["company"]["name"] == "TechStore"
    assert company["payment"]["methods"] == ["pix", "credit_card"]


def test_refund_policy_documents_yaml_numbers() -> None:
    """Refund markdown must mention the canonical window, threshold, and fee."""
    company = load_company_config()
    text = REFUND_POLICY.read_text(encoding="utf-8")
    window = str(company["refund"]["standard_window_days"])
    threshold = str(int(company["refund"]["approval_threshold_brl"]))
    rate = company["refund"]["restocking_fee_rate"]
    legal = str(company["withdrawal"]["legal_days"])
    assert window in text
    assert threshold in text
    assert legal in text
    assert "0.10" in text or "10%" in text or str(rate) in text


def test_payment_documents_list_pix_and_credit_card_only() -> None:
    """Payment Documents name v1.0 methods and omit boleto and debit."""
    text = PAYMENT_POLICY.read_text(encoding="utf-8")
    assert "pix" in text
    assert "credit_card" in text
    assert "boleto" not in text
    assert "debit_card" not in text


def test_company_overview_describes_techstore() -> None:
    """Overview Document names TechStore as a Brazilian electronics retailer."""
    text = OVERVIEW.read_text(encoding="utf-8")
    assert "TechStore" in text
    assert "Brazilian" in text or "Brazil" in text
    assert "electronics" in text.lower()
    assert "NexaCommerce" not in text


def test_knowledge_documents_do_not_name_nexacommerce() -> None:
    """Customer-facing Documents must not mention the retired merchant name."""
    for path in KB_ROOT.rglob("*.md"):
        if "_eval_injection" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "NexaCommerce" not in text, path
