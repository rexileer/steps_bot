from sqlalchemy import select

from app.steps_bot.db.models.captions import BotSetting
from app.steps_bot.db.repo import get_session


class SettingsService:
    @staticmethod
    async def get_setting(key: str) -> str | None:
        async with get_session() as session:
            result = await session.execute(
                select(BotSetting.value).where(BotSetting.key == key)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def set_setting(key: str, value: str) -> None:
        async with get_session() as session:
            setting = await session.get(BotSetting, key)
            if setting:
                setting.value = value
            else:
                session.add(BotSetting(key=key, value=value))
