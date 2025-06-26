from __future__ import annotations

import enum

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.steps_bot.db.models.base import Base


class MediaType(str, enum.Enum):
    NONE = "none"
    PHOTO = "photo"
    VIDEO = "video"


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType), default=MediaType.NONE, nullable=False
    )
    telegram_file_id: Mapped[str | None] = mapped_column(String(255))
    media_url: Mapped[str | None] = mapped_column(String(1024))

    def __repr__(self) -> str:
        return f"<Content {self.slug}>"
