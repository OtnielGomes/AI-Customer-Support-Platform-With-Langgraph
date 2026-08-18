"""Identity-first evaluation: logged-in customers are not re-identified."""

from app.evaluation.datasets.nexa_cases import NEXA_DATASET
from app.evaluation.evaluators import evaluate_identity_first


def test_nexa_cases_carry_customer_email() -> None:
    """Fixtures should include the portal login email after generate."""
    assert NEXA_DATASET
    with_email = [case for case in NEXA_DATASET if case.get("customer_email")]
    assert with_email, "Re-run generate_data.py so scenarios.json includes customer_email"


def test_identity_first_rejects_email_prompt() -> None:
    """Asking a logged-in customer for email fails the evaluator."""
    bad = evaluate_identity_first(
        "Pode confirmar o seu e-mail para eu localizar o pedido?",
        order_count=1,
    )
    good = evaluate_identity_first(
        "Vi o pedido ORD-01001 entregue em 10/01. Posso ajudar com o reembolso da cobrança duplicada.",
        order_count=1,
    )
    assert bad["passed"] is False
    assert good["passed"] is True


def test_identity_first_single_order_must_not_ask_for_number() -> None:
    """A customer with one order must not be asked for the order id."""
    bad = evaluate_identity_first(
        "Qual o número do pedido que você quer consultar?",
        order_count=1,
    )
    listing = evaluate_identity_first(
        "Encontrei dois pedidos: ORD-01001 entregue e ORD-01008 em trânsito. Qual deles?",
        order_count=2,
    )
    assert bad["passed"] is False
    assert listing["passed"] is True
