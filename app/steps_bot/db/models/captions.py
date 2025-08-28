from __future__ import annotations

import enum

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.steps_bot.db.models.base import Base


class MediaType(str, enum.Enum):
    """Тип медиа для контента."""
    NONE = "none"
    PHOTO = "photo"
    VIDEO = "video"


def enum_values(enum_cls):
    """Возвращает список значений Enum для SQLAlchemy."""
    return [member.value for member in enum_cls]


class Content(Base):
    """Контент для сообщений бота с поддержкой локального файла, URL и кэшируемого file_id."""
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    media_type: Mapped[MediaType] = mapped_column(
        Enum(
            MediaType,
            values_callable=enum_values,
            name="mediatype",
            create_type=True,
        ),
        default=MediaType.NONE,
        nullable=False,
    )
    telegram_file_id: Mapped[str | None] = mapped_column(String(255))
    media_url: Mapped[str | None] = mapped_column(String(1024))
    media_file: Mapped[str | None] = mapped_column(String(512))

    def __repr__(self) -> str:
        return f"<Content {self.slug}>"


class BotSetting(Base):
    """Пара ключ-значение для настроек бота, используемых сервисом SettingsService."""
    __tablename__ = "bot_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"<BotSetting {self.key}={self.value}>"
