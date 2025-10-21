from __future__ import annotations

import enum
import datetime as dt
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.steps_bot.db.models.base import Base
from app.steps_bot.db.models.captions import MediaType
from app.steps_bot.db.utils import enum_values

class CatalogCategory(Base):
    __tablename__ = "catalog_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    products: Mapped[List["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_categories.id", ondelete="SET NULL")
    )
    category: Mapped["CatalogCategory"] = relationship(back_populates="products")

    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    media_type: Mapped[MediaType] = mapped_column(
        Enum(
            MediaType,
            values_callable=enum_values,
            name='mediatype',
        ),
        default=MediaType.NONE,
        nullable=False,
    )
    telegram_file_id: Mapped[Optional[str]] = mapped_column(String(255))
    media_url: Mapped[Optional[str]] = mapped_column(String(1024))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    product_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class OrderStatus(str, enum.Enum):
    NEW = "new"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            values_callable=enum_values,
            name="orderstatus"
        ),
        default=OrderStatus.NEW,
        nullable=False,
    )
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)
    pvz_id: Mapped[Optional[str]] = mapped_column(ForeignKey("pvz.id"), nullable=True)
    recipient_first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recipient_last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class UserAddress(Base):
    __tablename__ = "user_addresses"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    city: Mapped[str] = mapped_column(String(60))
    street: Mapped[str] = mapped_column(String(120))
    postcode: Mapped[str] = mapped_column(String(10))
