from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def make_row_kb(items: list[str]) -> ReplyKeyboardMarkup:
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)
def disagree_kb():
    kb = [
        [KeyboardButton(text="Нет")],
    ]
    start_kb = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    return start_kb
