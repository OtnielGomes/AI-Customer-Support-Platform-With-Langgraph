"""Shared StrEnum values for NexaCommerce operational tables."""

import enum


class CustomerTier(enum.StrEnum):
    """Customer loyalty segment."""

    STANDARD = "standard"
    SILVER = "silver"
    GOLD = "gold"
    ENTERPRISE = "enterprise"


class AccountStatus(enum.StrEnum):
    """Customer account lifecycle status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class OrderStatus(enum.StrEnum):
    """Order fulfillment status."""

    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentStatus(enum.StrEnum):
    """Payment processing status."""

    PENDING = "pending"
    AUTHORIZED = "authorized"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(enum.StrEnum):
    """Supported payment methods."""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PIX = "pix"
    BOLETO = "boleto"


class ShipmentStatus(enum.StrEnum):
    """Carrier shipment status."""

    PROCESSING = "processing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    LOST = "lost"


class ReturnStatus(enum.StrEnum):
    """Return request status."""

    REQUESTED = "requested"
    PENDING_INSPECTION = "pending_inspection"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReturnReason(enum.StrEnum):
    """Reason a customer opened a return."""

    DEFECTIVE_PRODUCT = "defective_product"
    WRONG_ITEM = "wrong_item"
    CUSTOMER_PREFERENCE = "customer_preference"
    MISSING_PARTS = "missing_parts"
    OTHER = "other"


class InspectionStatus(enum.StrEnum):
    """Physical inspection outcome for a return."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    NOT_REQUIRED = "not_required"


class RefundStatus(enum.StrEnum):
    """Refund request status."""

    REQUESTED = "requested"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    DENIED = "denied"


class ProductCategory(enum.StrEnum):
    """Sellable product category."""

    SMARTPHONES = "smartphones"
    LAPTOPS = "laptops"
    MONITORS = "monitors"
    HEADPHONES = "headphones"
    KEYBOARDS = "keyboards"
    ACCESSORIES = "accessories"
