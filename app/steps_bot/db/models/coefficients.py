from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    Integer,
    SmallInteger,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.steps_bot.db.models.base import Base
from app.steps_bot.db.models.walk import WalkForm


class TemperatureCoefficient(Base):
    __tablename__ = "temperature_coefficients"
    __table_args__ = (
        CheckConstraint("min_temp_c <= max_temp_c", name="ck_temp_range"),
        Index("ix_tempcoeff", "walk_form", "min_temp_c", "max_temp_c", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    walk_form: Mapped[WalkForm] = mapped_column(Enum(WalkForm), nullable=False)
    min_temp_c: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    max_temp_c: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    coefficient: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TempCoef {self.walk_form.value} {self.min_temp_c}-{self.max_temp_c}>"
