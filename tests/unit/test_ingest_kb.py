"""Tests for knowledge-base path mapping."""

from pathlib import Path

from app.retrieval.ingest_paths import infer_domain, should_ingest


def test_infer_domain_policies() -> None:
    """Refund and warranty docs map to billing; shipping to logistics."""
    assert infer_domain(Path("data/knowledge_base/policies/refund_policy.md")) == "billing"
    assert infer_domain(Path("data/knowledge_base/policies/warranty_policy.md")) == "billing"
    assert infer_domain(Path("data/knowledge_base/policies/shipping_policy.md")) == "logistics"
    assert infer_domain(Path("data/knowledge_base/procedures/identity_verification.md")) == "account"
    assert infer_domain(Path("data/knowledge_base/company/company_overview.md")) == "general"


def test_should_skip_injection_corpus() -> None:
    """Injection fixtures are skipped unless explicitly enabled."""
    path = Path("data/knowledge_base/_eval_injection/shipping_faq.md")
    assert should_ingest(path, include_injection=False) is False
    assert should_ingest(path, include_injection=True) is True
