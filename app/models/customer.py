"""Customer ORM model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import AccountStatus, CustomerTier
from app.persistence import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.ticket import Ticket


def _runtime_public_id() -> str:
    """Generate a unique public_id for customers created outside the seeder."""
    return f"CUST-{uuid.uuid4().hex[:8].upper()}"


class Customer(Base):
    """Customer account linked to orders and support tickets."""

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        default=_runtime_public_id,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    customer_tier: Mapped[CustomerTier] = mapped_column(
        Enum(CustomerTier, name="customer_tier", values_callable=lambda x: [e.value for e in x]),
        default=CustomerTier.STANDARD,
    )
    account_status: Mapped[AccountStatus] = mapped_column(
        Enum(
            AccountStatus,
            name="account_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AccountStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
