import asyncio
import logging
import sys
import aiogram
from os import getenv
from config import TOKEN
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardBuilder

start_text = "Игра в 'Перудо'.\n"\
             " Каждый игрок получет по 5 игральных костей, затем определяется очередность хода. Каждый игрок перемешивает свои кости и в закрытую смотрит на выпавшие номиналы на костях.\n"\
             " Первый игрок решает какой ход он делает. Для произведения хода стоит указать какое, по мнению игрока, количество костей одного номинала лежит за столом.\n"\
             "      Например:\n"\
             "  Ходит первый игрок, смотрит на свои кости и говорит: 'Я считаю, что за столом две тройки (две кости, с номиналом 'три')'\n"\
             "  Но! В Перудо, кости номинала 'один', считаются костями любого номинала!\n"\
             "  Следующий игрок, в ответ на его заявление, может сделать следующие действия:\n"\
             "      1. Увеличить в НОМИНАЛ или КОЛИЧЕСТВО кубиков такого номинала.\n"\
             "      2. Не согласиться с заявлением предыдущего игрока.\n"\
             "  В случае 1 - В Перудо, можно только повышать ставку (Вплоть до единицы)! Повысить можно что-то одно: номинал кости или количество таких костей.\n"\
             "Например: Ставка - 'Две тройки'. Можно сказать: 'Я считаю, что за столом ТРИ тройки' или даже 'ШЕСТЬ троек'.\n"\
             "Например: Ставка - 'Две тройки'. Можно сказать: 'Я считаю, что за столом две ЧЕТВЕРКИ' или даже 'две ЕДИНИЦЫ', к слову, порядок выглядит так: 2-3-4-5-6-1 - т.е. после шестерки повышать можно только на единицу. "\
             "  В случае 2 - Раунд заканчивается, все игроки раскрывают свои кости и производится подсчет. Существует три исхода, предположим текущее заявление 'Четыре тройки': \n"\
             "          Исход 1: При подсчете количества кубиков (включая единицы, т.е. считая еденицу как тройку), оказалось, что за столом количество кубиков БОЛЬШЕ, чем было заявлено (Учитывая наш пример, количество троек оказалось равным ПЯТИ, при заявленых четырех тройках)."\
             "В таком случае, игрок, который НЕ СОГЛАСИЛСЯ с заявлением (четыре тройки), оказался не прав (Количество троек - 5) - ОН теряет одну одну свою кость и начинается новый раунд.\n"\
             "          Исход 2: При подсчете количества кубиков (включая единицы, т.е. считая еденицу как тройку), оказалось, что за столом количество кубиков МЕНЬШЕ, чем заявлено (Учитывая наш пример, количество троек оказалось равным ТРЁМ, при заявленых четырех тройках)."\
             "В таком случае, игрок, который ДАЛ заявление (Четыре тройки), оказался не прав (Количество троек - 3) - ОН теряет одну одну свою кость и начинается новый раунд.\n"\
             "          Исход 3: При подсчете количества кубиков (включая единицы, т.е. считая еденицу как тройку), оказалось, что за столом количество кубиков РОВНО СТОЛЬКО ЖЕ, сколько и заявлено (Учитывая наш пример, количество троек оказалось равным ЧЕТЫРЁМ, при заявленых четырех тройках)."\
             "В таком случае, игрок, который ДАЛ заявление (Четыре тройки), оказался ПРАВ (Количество троек - 4), кость теряет игрок, не согласившийся с таким завялением и начинается новый раунд.\n"\
             "  ЦЕЛЬ ИГРЫ: Остаться ПОСЛЕДНИМ игроком у которого ЕСТЬ КОСТИ.\n"\
             "  ДОП. правило: Игрок, у которого остается ОДНА единственная кость, может объявить в любое время перед началом раунда раунд 'Мапута'.\n"\
             "  В раунде 'Мапута' единицы становятся ОБЫЧНЫМИ костями и перестают учитыватсья в ходе подсчета кубиков другого номинала, после вскрытия в конце раунда.\n"\
             "  УДАЧИ!"

game_master = ({"id": 0, "fst_name": "", "snd_name": ""})
game_players = ({"id": 0, "fst_name": "", "snd_name": ""})
game_max_players = 4


bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

async def main():

    await dp.start_polling(bot)



class Player():
    p_id = 0 #player id
    p_name = "name" #player tg name
    dice_amount = 5
    dice_value = [""] #contains values of dieces
class Game():
    def __init__(self):
        self.queue = [] #contains IDs
        self.queue_names = [] #contains Names
    def add_queue(self, p_id):
        if(p_id in self.queue):
            return False
        else:
            self.queue.append(p_id)
            return True

g = Game()



###

@dp.message(Command("id"))
async def any_message(message: Message):
    await message.answer(f"{message.from_user.id}")


###

#KEYBOARD START-----------------------------------------------------------------------------------
@dp.message(CommandStart())
async def csh(message: Message):
    global chat_id
    kb = [
        [types.KeyboardButton(text="Начать")],
        [types.KeyboardButton(text="Правила")]

    ]
    start_kb = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(f"Привет, {hbold(message.from_user.full_name)}!", reply_markup=start_kb)
    chat_id = message.chat.id


@dp.message(F.text.lower() == "правила")
async def display_rules(message : Message):
    await message.answer(start_text)

@dp.message(F.text.lower() == "начать")
async def game_create(message : Message):
    if (game_master["id"] == 0):
        game_master["id"], game_master["fst_name"], game_master["snd_name"] = message.from_user.id, message.from_user.first_name, message.from_user.last_name
        i = 4
        builder = InlineKeyboardBuilder()
        await message.answer(f"{message.from_user.first_name} - Cоздает лобби игры")
        for i in range(4,7):
            builder.add(types.InlineKeyboardButton(
            text=f"{i}",
            callback_data=f"p{i}")
            )
        builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"), types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct")) ###########CALLBACK####################################
        await message.answer(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())
    else:
        await message.answer(f"{game_master['fst_name']}, у вас уже есть активное лобби!")

@dp.callback_query(F.data == "distruct")
async def delete_lobby(callback : types.CallbackQuery):
    global game_master
    await callback.message.answer(f"{game_master['fst_name']} - Удаляет лобби!")
    await callback.message.delete()
    game_master = ({"id": 0, "fst_name": "", "snd_name": ""})
    game_players = ({"id": 0, "fst_name": "", "snd_name": ""})
    game_max_players = 4



@dp.callback_query(F.data == "p4")
async def p4(callback: types.CallbackQuery):
    game_max_players = 4
    builder = InlineKeyboardBuilder()
    for i in range(4, 7):
        builder.add(types.InlineKeyboardButton(
            text=f"{i}",
            callback_data=f"p{i}")
        )
    builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"),
                types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct"))
    await callback.message.edit_text(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "p5")
async def p5(callback: types.CallbackQuery):
    game_max_players = 5
    builder = InlineKeyboardBuilder()
    for i in range(4, 7):
        builder.add(types.InlineKeyboardButton(
            text=f"{i}",
            callback_data=f"p{i}")
        )
    builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"),
                types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct"))
    await callback.message.edit_text(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "p6")
async def p6(callback: types.CallbackQuery):
    game_max_players = 6
    builder = InlineKeyboardBuilder()
    for i in range(4, 7):
        builder.add(types.InlineKeyboardButton(
            text=f"{i}",
            callback_data=f"p{i}")
        )
    builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"),
                types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct"))
    await callback.message.edit_text(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())

@dp.message(F.text.lower() == "начать2")
async def display_rules(message : Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Присоединиться",
        callback_data='id')
    )
    await message.answer("Очередь на игру", reply_markup=builder.as_markup())
    queue_msg_id = message.message_id
@dp.callback_query(F.data == "id")
async def send_message(callback: types.CallbackQuery):
    if len(g.queue_names) <= game_max_players:
        if(g.add_queue(callback.from_user.id) == True):
            g.queue_names.append(callback.from_user.first_name)
            await callback.message.answer(f"{callback.from_user.first_name}, вы встали в очередь на игру")
        else:
            await callback.message.answer(f"{callback.from_user.first_name}, Вы уже стоите в очереди на игру")
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(
            text="Присоединиться",
            callback_data='id')
        )
        await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=f"Очередь на игру({len(g.queue_names)}/{game_max_players}):\n{g.queue_names}",reply_markup=builder.as_markup())
    else:
        await callback.message.answer('Очередь заполнена')
#KEYBOARD START-----------------------------------------------------------------------------------



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    asyncio.run(main())