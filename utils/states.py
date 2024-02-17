from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.state import State
from aiogram.filters.state import StatesGroup

class Turn(StatesGroup):
    israise = State() #Состояние, отвечающие за отслеживание ставки, которое ожидает ставку от пользователя
    switch_turn = State() #Состояние, отвечающие за переход хода
    raise_or_open = State() #Состояние, отвечающие за поднятие ставки или вскрытия всех костей
    state_list = [israise, switch_turn, raise_or_open]