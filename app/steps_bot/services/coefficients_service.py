from __future__ import annotations

from sqlalchemy import select

from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models.walk import WalkForm, WalkFormCoefficient
from app.steps_bot.db.models.coefficients import TemperatureCoefficient


async def get_walk_form_coef(form: WalkForm) -> int:
    async with get_session() as s:
        q = select(WalkFormCoefficient.coefficient).where(WalkFormCoefficient.walk_form == form)
        res = await s.execute(q)
        coef = res.scalar_one_or_none()
        return int(coef or 1)


async def get_temperature_coef(form: WalkForm, temp_c: int | None) -> int:
    if temp_c is None:
        return 1
    async with get_session() as s:
        q = (
            select(TemperatureCoefficient.coefficient)
            .where(TemperatureCoefficient.walk_form == form)
            .where(TemperatureCoefficient.min_temp_c <= temp_c)
            .where(TemperatureCoefficient.max_temp_c >= temp_c)
        )
        res = await s.execute(q)
        coef = res.scalar_one_or_none()
        return int(coef or 1)


async def get_total_multiplier(form: WalkForm, temp_c: int | None = None) -> int:
    """Итоговый множитель = коэффициент формы × (опционально) температурный коэффициент."""
    base = await get_walk_form_coef(form)
    temp = await get_temperature_coef(form, temp_c)
    return max(1, base * temp)
