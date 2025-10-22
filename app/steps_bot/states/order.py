from aiogram.fsm.state import State, StatesGroup
from pydantic import BaseModel


class OrderInput(BaseModel):
    product_id: int
    delivery_type: str
    city: str
    pvz_code: str | None = None
    address: str | None = None
    full_name: str
    phone: str


class OrderStates(StatesGroup):
    choosing_delivery_type = State()
    entering_city = State()
    entering_street = State()
    entering_pvz_or_address = State()
    entering_full_name = State()
    entering_phone = State()
    confirming = State()
