from aiogram.fsm.state import State, StatesGroup


class WalkStates(StatesGroup):
    # Собака
    waiting_for_dog_walk_location = State()
    # Коляска
    waiting_for_roller_walk_location = State()
    # Собака + коляска
    waiting_for_rolldog_walk_location = State()
