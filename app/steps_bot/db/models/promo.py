from datetime import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base


class PromoGroup(Base):
    """
    Группа промокодов с процентной скидкой.
    """
    __tablename__ = "promo_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    codes: Mapped[list["PromoCode"]] = relationship(
        "PromoCode",
        back_populates="group",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="ck_promo_groups_discount_percent"),
        CheckConstraint("price_points >= 0", name="ck_promo_groups_price_points"),
    )


class PromoCode(Base):
    """
    Промокод без сроков действия.
    """
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("promo_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    group: Mapped[PromoGroup] = relationship("PromoGroup", back_populates="codes")

    __table_args__ = (
        UniqueConstraint("code", name="uq_promo_codes_code"),
        CheckConstraint("max_uses >= 0", name="ck_promo_codes_max_uses"),
        CheckConstraint("used_count >= 0", name="ck_promo_codes_used_count"),
    )
