from __future__ import annotations

import enum
import datetime as dt
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.steps_bot.db.models.base import Base


class FamilyInviteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELED = "canceled"


def enum_values(enum_cls):
    return [member.value for member in enum_cls]


class Family(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    members: Mapped[List["User"]] = relationship(back_populates="family")
    invitations: Mapped[List["FamilyInvitation"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Family {self.id}:{self.name}>"


class FamilyInvitation(Base):
    __tablename__ = "family_invitations"
    __table_args__ = (
        UniqueConstraint("family_id", "invitee_id", name="uq_invite_once"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invitee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[FamilyInviteStatus] = mapped_column(
        Enum(
            FamilyInviteStatus,
            values_callable=enum_values,
            name="familyinvitestatus",
        ),
        default=FamilyInviteStatus.PENDING,
        index=True,
        nullable=False,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    responded_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))

    family: Mapped[Family] = relationship(back_populates="invitations")

    def __repr__(self) -> str:
        return f"<Invite {self.id} {self.status.value}>"
