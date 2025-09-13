from __future__ import annotations

import enum
import datetime as dt
from typing import Optional

from sqlalchemy import DateTime, Enum, Integer, String, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.steps_bot.db.models.base import Base
from app.steps_bot.db.models.captions import MediaType
from app.steps_bot.db.utils import enum_values


class BroadcastStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    text: Mapped[Optional[str]] = mapped_column(Text)

    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, values_callable=enum_values, name="mediatype"),
        default=MediaType.NONE,
        nullable=False,
    )
    telegram_file_id: Mapped[Optional[str]] = mapped_column(String(255))
    media_url: Mapped[Optional[str]] = mapped_column(String(1024))
    media_file: Mapped[Optional[str]] = mapped_column(String(1024))

    scheduled_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), index=True)
    sent_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[BroadcastStatus] = mapped_column(
        Enum(BroadcastStatus, values_callable=enum_values, name="broadcaststatus"),
        default=BroadcastStatus.PENDING,
        nullable=False,
        index=True,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_broadcast_due", "status", "scheduled_at"),
    )



