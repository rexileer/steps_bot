from __future__ import annotations

import datetime as dt
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.steps_bot.db.models.base import Base


class PVZ(Base):
    """
    Пункт выдачи заказов (ПВЗ).
    
    Поля:
    - id: уникальный идентификатор (строка, первичный ключ)
    - full_address: полный адрес ПВЗ
    - created_at: дата создания записи
    """
    __tablename__ = "pvz"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    full_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PVZ {self.id}>"
