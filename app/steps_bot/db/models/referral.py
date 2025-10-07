from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.steps_bot.db.models.base import Base

if TYPE_CHECKING:
    from app.steps_bot.db.models.user import User


class Referral(Base):
    """Модель для хранения реферальных связей"""
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    
    # Пользователь, который был приглашен
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # Каждый пользователь может быть приглашен только один раз
        nullable=False,
        index=True,
    )
    
    # Пользователь, который пригласил
    inviter_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Количество баллов, начисленных пригласившему за этого реферала
    reward_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Дата создания реферальной связи
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        backref="referred_by_relation",
    )
    inviter: Mapped[User] = relationship(
        "User",
        foreign_keys=[inviter_id],
        backref="referrals_made",
    )

    def __repr__(self) -> str:
        return f"<Referral user={self.user_id} inviter={self.inviter_id}>"


