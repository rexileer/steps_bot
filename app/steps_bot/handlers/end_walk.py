from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.steps_bot.services.walk_finish import finish_walk

router = Router()


@router.callback_query(F.data == "end_walk")
async def end_dog_walk(callback: CallbackQuery) -> None:
    """Завершает прогулку по кнопке и редактирует это же сообщение."""
    await finish_walk(
        callback.message,
        target_message_id=callback.message.message_id,
        user_id=callback.from_user.id,
    )
    await callback.answer()
