import aiogram
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
from Body import dp, Player
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram import F
import utils.states as s

form_router = Router()

async def turn_message(callback: types.CallbackQuery, turn_order, current_person):
    view_order = ""
    for i in turn_order:
        if i == len(turn_order):
            view_order += i
        else:
            view_order += f"{i}, "
    await callback.message.answer(f"Ходит: {current_person}\r\nОчередность ходов: {view_order}")

def string_to_format(text):
    original_string = text
    ms = re.sub(r'\s', '', original_string)
    error_keys = [",", ".", "`", "[", "]", "{", "}", '/', "|", ";", ":"]
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
    new_ms = ""
    for i in ms:
        if i not in error_keys and i in keys:
            new_ms += "".join(i)
    if len(new_ms) != 2:
        return False
    else:
        return True, new_ms
def bet_to_format(text):
    keys = {"1":"Единица", "2":"Двойка", "3":"Тройка", "4":"Четверка", "5":"Пятерка", "6":"Шестерка"}
    if text[0] in keys:
        return keys[text[0]]
