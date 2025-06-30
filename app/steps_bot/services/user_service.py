from typing import Optional

from sqlalchemy import select

from app.steps_bot.db.repo import get_session
from app.steps_bot.db.models.user import User


async def register_user(
    telegram_id: int,
    username: Optional[str],
    phone: str,
    email: str,
) -> User:
    async with get_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))

        if user:
            if phone and not user.phone:
                user.phone = phone
            if email and not user.email:
                user.email = email
        else:
            user = User(
                telegram_id=telegram_id,
                username=username,
                phone=phone,
                email=email,
            )
            session.add(user)

        await session.flush()
        return user


async def get_user(telegram_id: int) -> Optional[User]:
    async with get_session() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))