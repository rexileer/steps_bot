from aiogram.fsm.state import StatesGroup, State


class FamilyRename(StatesGroup):
    waiting_for_name = State()
