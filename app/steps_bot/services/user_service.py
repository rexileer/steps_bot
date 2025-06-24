import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.steps_bot.db.models import User


async def create_or_update_user(
    session: AsyncSession,
    tg_id: int,
    first_name: str = '',
    last_name: str = '',
    company: str = '',
    phone: str = '',
) -> User:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    now = dt.datetime.utcnow()

    if user:
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if company:
            user.company = company
        if phone:
            user.phone = phone
        user.last_activity_at = now
    else:
        user = User(
            tg_id=tg_id,
            first_name=first_name,
            last_name=last_name,
            company=company,
            phone=phone,
            registered_at=now,
            last_activity_at=now,
        )
        session.add(user)

    return user


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()


async def get_admin_ids(session):
    result = await session.execute(select(User.tg_id).where(User.is_admin == True))
    return [row[0] for row in result.all()]