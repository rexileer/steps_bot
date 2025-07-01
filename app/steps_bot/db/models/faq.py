from __future__ import annotations

import enum
from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.steps_bot.db.models.base import Base


class FAQMediaType(str, enum.Enum):
    NONE = "none"
    PHOTO = "photo"
    VIDEO = "video"


def enum_values(enum_cls):
    return [member.value for member in enum_cls]


class FAQ(Base):
    __tablename__ = "faq_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    media_type: Mapped[FAQMediaType] = mapped_column(
        Enum(
            FAQMediaType,
            values_callable=enum_values,
            name="faqmediatype",
        ),
        default=FAQMediaType.NONE,
        nullable=False,
    )
    telegram_file_id: Mapped[str | None] = mapped_column(String(255))
    media_url: Mapped[str | None] = mapped_column(String(1024))

    def __repr__(self) -> str:
        return f"<FAQ {self.slug}>"
