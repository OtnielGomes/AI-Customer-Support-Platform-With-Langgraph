# company.yaml — policy v1.0 constants

Add these keys to `data/company/company.yaml` (extend [synthetic-data assets/company.yaml.example](../synthetic-data/assets/company.yaml.example)). Policy markdown and `app/policies/rules.py` **must** match.

```yaml
policy:
  version: "1.0"
  effective_date: "2026-08-01"
  brand: TechStore
  operation: web_only
  marketplace: false
  physical_stores: false

payment:
  methods:
    - pix
    - credit_card
  off_channel_pix_forbidden: true
  pix_timeout_hours: 24          # order cancelled if unpaid — tune in generator
  fraud_review_enabled: true

withdrawal:
  # CDC Art. 49 — arrependimento (remote purchase)
  legal_days: 7

refund:
  standard_window_days: 30         # commercial preference refund (post-delivery)
  approval_threshold_brl: 1000
  restocking_fee_rate: 0.10
  original_payment_method_only: true
  identity_verification_required: true

warranty:
  legal_durable_days: 90         # CDC vícios aparentes — produtos duráveis
  default_days: 90               # contractual default (non-durable categories)
  computers_days: 365
  smartphones_days: 365
  electronics_inspection_after_days: 7

shipping:
  damage_report_hours: 48        # operational logistics window (§8)
  no_store_pickup: true
  # delivery_methods: express_sedex / standard — see synthetic-data yaml

cancellation:
  allowed_before_shipment: true
  shipped_requires_return_flow: true
  auto_cancel_unpaid: true

fraud:
  additional_verification_enabled: true
  block_or_cancel_on_suspicion: true
```

## Mapping policy sections → yaml keys

| Policy § | yaml key(s) |
|----------|-------------|
| 5 Pagamentos | `payment.methods`, `payment.off_channel_pix_forbidden` |
| 6 Cancelamento | `cancellation.*` |
| 7 Entrega | `shipping.delivery_methods`, `shipping.no_store_pickup` |
| 8 Avarias | `shipping.damage_report_hours` |
| 10 Arrependimento | `withdrawal.legal_days` |
| 11–12 Trocas/garantia | `warranty.*`, `refund.*` |
| 14 Reembolso | `refund.*`, `payment.methods` (restitution path) |
| 15 Fraude | `fraud.*` |

## Labels (customer-facing)

Keep enum labels in `labels.*` (synthetic-data). Policy docs use Portuguese in FAQ; **numbers** always from yaml.
