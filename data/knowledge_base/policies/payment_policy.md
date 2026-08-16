# NexaCommerce Payment Policy

1. Supported methods: credit_card, debit_card, pix, boleto.
2. Two `paid` payments of the same amount on one order are a duplicate charge.
3. Duplicate charges: refund one payment via the original method after identity verification.
4. Multiple failed payments plus a high-value capture is a fraud-risk cluster; do not auto-refund.
5. Agents must not reveal full payment credentials or PAN data.
