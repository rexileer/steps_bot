from aiogram.fsm.state import StatesGroup, State


class FamilyCreation(StatesGroup):
    waiting_for_name = State()