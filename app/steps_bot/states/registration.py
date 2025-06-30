from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_for_consent = State() 
    waiting_for_phone = State()
    waiting_for_email = State()