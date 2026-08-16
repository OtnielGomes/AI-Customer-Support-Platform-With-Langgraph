"""Product catalog ORM model."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import ProductCategory
from app.persistence import Base

if TYPE_CHECKING:
    from app.models.order import OrderItem


class Product(Base):
    """Sellable catalog item."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[ProductCategory] = mapped_column(
        Enum(
            ProductCategory,
            name="product_category",
            values_callable=lambda x: [e.value for e in x],
        ),
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    final_sale: Mapped[bool] = mapped_column(Boolean, default=False)
    warranty_days: Mapped[int] = mapped_column(Integer, default=90)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")
