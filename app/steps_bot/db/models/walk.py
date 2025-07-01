from __future__ import annotations

import enum
import datetime as dt

from sqlalchemy import DateTime, Enum, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.steps_bot.db.models.base import Base
from app.steps_bot.db.utils import enum_values


class WalkForm(str, enum.Enum):
    STROLLER = "stroller"
    DOG = "dog"
    STROLLER_DOG = "stroller_dog"


class WalkFormCoefficient(Base):
    __tablename__ = "walk_form_coefficients"

    walk_form: Mapped[WalkForm] = mapped_column(
        Enum(WalkForm, values_callable=enum_values, name="walkform"),
        primary_key=True,
    )
    coefficient: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<WalkCoef {self.walk_form.value}={self.coefficient}>"
