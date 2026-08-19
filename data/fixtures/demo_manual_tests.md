# Demo customer — manual agent tests

Portal login: `demo@test.com.br` (Demo Tester).
Open a new conversation, pick the order, and paste the suggested message.

| Scenario | Order | Kind | Message | Expected tools | Policy | Expected resolution | Human? |
|----------|-------|------|---------|----------------|--------|---------------------|--------|
| `SCN-DEMO-01` | `ORD-01013` | `double_payment` | Fui cobrado duas vezes pelo mesmo pedido. | `get_order, get_payments` | `payment_policy` | `refund_duplicate_charge` | no |
| `SCN-DEMO-02` | `ORD-01014` | `delayed_shipment` | Meu pedido esta atrasado. | `get_order, get_shipment` | `shipping_policy` | `explain_delay` | no |
| `SCN-DEMO-03` | `ORD-01015` | `delivered_missing` | Aparece como entregue, mas nao recebi. | `get_order, get_shipment` | `shipping_policy` | `investigate_missing_delivery` | yes |
| `SCN-DEMO-04` | `ORD-01016` | `refund_outside_window` | Quero meu dinheiro de volta. | `get_order, check_refund_eligibility` | `refund_policy` | `deny_outside_window` | no |
| `SCN-DEMO-05` | `ORD-01017` | `defective_warranty` | Meu notebook chegou com defeito. Quero reembolso. | `get_order, check_refund_eligibility` | `warranty_policy` | `warranty_exception` | yes |
| `SCN-DEMO-06` | `ORD-01018` | `high_value_refund` | Quero reembolso do meu notebook de alto valor. | `get_order, check_refund_eligibility` | `refund_policy` | `escalate_high_value_refund` | yes |
| `SCN-DEMO-07` | `ORD-01019` | `cancel_after_ship` | Quero cancelar meu pedido. | `get_order, get_shipment` | `shipping_policy` | `deny_cancel_use_return` | no |
| `SCN-DEMO-08` | `ORD-01020` | `final_sale` | Quero devolver este item. | `get_order, check_refund_eligibility` | `return_policy` | `deny_final_sale` | no |
| `SCN-DEMO-09` | `ORD-01021` | `failed_payment` | Tentei pagar e o cartao foi recusado. O que aconteceu com o pedido? | `get_order, get_payments` | `payment_policy` | `explain_failed_payment` | no |
| `SCN-DEMO-10` | `ORD-01022` | `happy_path` | Onde esta meu pedido? | `get_order, get_shipment` | `shipping_policy` | `share_tracking` | no |
