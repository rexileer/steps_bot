from aiogram.fsm.state import StatesGroup, State


class FamilyInvite(StatesGroup):
    waiting_for_username = State()