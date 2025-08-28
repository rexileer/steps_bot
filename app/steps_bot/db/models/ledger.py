from __future__ import annotations

import enum
import datetime as dt
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.steps_bot.db.models.base import Base
from app.steps_bot.db.utils import enum_values


class OwnerType(str, enum.Enum):
    """
    Тип владельца баланса, к которому относится операция.
    """
    USER = "user"
    FAMILY = "family"


class OperationType(str, enum.Enum):
    """
    Семантика операции по балансу.
    """
    STEPS_ACCRUAL = "steps_accrual"
    PURCHASE = "purchase"
    PROMO_ACCRUAL = "promo_accrual"
    REFUND = "refund"
    MANUAL_ADJUST = "manual_adjust"
    TRANSFER = "transfer"


class LedgerEntry(Base):
    """
    Журнал операций по балансам пользователей и семей.

    Сумма хранится в целых единицах (баллы). Положительное значение — начисление,
    отрицательное — списание. Для покупок указывайте отрицательную сумму и,
    при наличии, связывайте с заказом.
    """
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint(
            "(owner_type = 'user' AND user_id IS NOT NULL AND family_id IS NULL) OR "
            "(owner_type = 'family' AND family_id IS NOT NULL AND user_id IS NULL)",
            name="ck_ledger_owner_fk",
        ),
        Index("ix_ledger_owner_created", "owner_type", "created_at"),
        Index("ix_ledger_user_created", "user_id", "created_at"),
        Index("ix_ledger_family_created", "family_id", "created_at"),
        Index("ix_ledger_operation_created", "operation", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    owner_type: Mapped[OwnerType] = mapped_column(
        Enum(OwnerType, values_callable=enum_values, name="ownertype"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    family_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    operation: Mapped[OperationType] = mapped_column(
        Enum(OperationType, values_callable=enum_values, name="operationtype"),
        nullable=False,
        index=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    order = relationship("Order", viewonly=True)

    def __repr__(self) -> str:
        return f"<LedgerEntry {self.id} {self.owner_type.value} {self.operation.value} {self.amount}>"
