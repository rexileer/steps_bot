from __future__ import annotations

import enum
import datetime as dt

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.steps_bot.db.models.base import Base

if TYPE_CHECKING:
    from app.steps_bot.db.models.family import Family, FamilyInvitation


class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username = mapped_column(String(64), unique=True, index=True)
    
    # ФИО заполняется на шаге оформления заказа
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    father_name: Mapped[Optional[str]] = mapped_column(String(100))

    last_lat: Mapped[Optional[float]] = mapped_column(Float)
    last_lon: Mapped[Optional[float]] = mapped_column(Float)
    step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    family_id: Mapped[Optional[int]] = mapped_column(ForeignKey("families.id", ondelete="SET NULL"), index=True)
    family: Mapped[Optional["Family"]] = relationship(back_populates="members")

    invites_sent: Mapped[List["FamilyInvitation"]] = relationship(
        primaryjoin="User.id==FamilyInvitation.inviter_id", viewonly=True
    )
    invites_received: Mapped[List["FamilyInvitation"]] = relationship(
        primaryjoin="User.id==FamilyInvitation.invitee_id", viewonly=True
    )

    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User {self.id} tg={self.telegram_id}>"
