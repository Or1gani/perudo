import asyncio
import logging
import sys
import aiogram.exceptions
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

game_master = ({}) # id:name
game_players = ({}) # -
id_needed_lobby = []
game_max_players = 4


bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

async def main():

    await dp.start_polling(bot)



class Player():
    p_id = 0 #player id
    p_name = "name" #player tg name
    dice_amount = 5
    dice_value = [""] #contain diece values
class Game():
    def __init__(self):
        self.lobby_id = 1
        self.queue_id = ({}) # msg_id : lobby_id
        self.queue_people = {}  #id_player : id_lobby
        self.queue_people_names = {} # name_player : msg_id
    def add_queue(self, p_id):
        if(p_id in self.queue):
            return False
        else:
            self.queue.append(p_id)
            return True
    def add_player(self, player_id, needed_lobby):
        if str(player_id) in self.queue_people:
            return False
        else:
            self.queue_people[f"{player_id}"] = needed_lobby
            return True

    def create_queue(self, game_master_id, msg_id):
        if game_master_id not in game_master:
            self.queue_id[f"{msg_id}"] = self.lobby_id
            self.lobby_id += 1

g = Game()

###not-for-user-debug

@dp.message(Command("id"))
async def any_message(message: Message):
    await message.answer(f"{message.from_user.id}")

###not-for-user-debug

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
    if message.from_user.first_name not in g.queue_people_names:
        global game_master
        if (str(message.from_user.id) not in game_master):
            game_master[f"{message.from_user.id}"] = message.from_user.first_name
            i = 4
            builder = InlineKeyboardBuilder()
            await message.answer(f"{message.from_user.first_name} - Cоздает лобби игры")
            for i in range(2,7):
                builder.add(types.InlineKeyboardButton(
                text=f"{i}",
                callback_data=f"p{i}")
                )
            builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"), types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct")) ###########CALLBACK####################################
            await message.answer(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())
        else:
            await message.answer(f"{game_master[f'{message.from_user.id}']}, у вас уже есть активное лобби!")
    else:
        await message.answer(f"{message.from_user.first_name}, к сожалению вы уже присоединились к активному лобби!")

@dp.message(F.text.lower() == "s")
async def learning(message : Message):
    #await message.answer(f"{message.from_user.first_name, type(message.from_user.first_name)}")
    await bot.send_message(chat_id='886945416', text="ХУЙ")


@dp.callback_query(F.data == "continue")
async def continue_game(callback : types.CallbackQuery):
    global game_master
    await callback.message.delete()
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Открыть Лобби", callback_data="open"), types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct"))
    await callback.message.answer(f"{game_master[f'{callback.from_user.id}']} - Открывает лобби", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "distruct")
async def delete_lobby(callback : types.CallbackQuery):
    global game_master
    global game_max_players
    global id_needed_lobby

    if str(callback.message.message_id) in g.queue_id:
        lobby_to_delete = g.queue_id[str(callback.message.message_id)]
    filtered_dict = {}
    for key, value in g.queue_people.items():
        if str(value) != str(lobby_to_delete):
            filtered_dict[key] = value
    g.queue_people = filtered_dict
    if str(callback.from_user.id) in game_master:
        await callback.message.answer(f"{game_master[f'{callback.from_user.id}']} - Удаляет лобби!")
        g.lobby_id -= 1
        try:
            g.queue_id.pop(f"{game_master[f'{callback.from_user.id}']}")
        except KeyError:
            pass
        game_master.pop(f"{callback.from_user.id}")
        game_players.clear()
        game_max_players = 4
        await callback.message.delete()
    try:

        if str(callback.message.message_id) in g.queue_id:
            g.queue_id.pop(str(callback.message.message_id))
        filtered_dict = {}
        for key, value in g.queue_people_names.items():
            if str(value) != str(callback.message.message_id):
                filtered_dict[key] = value
        g.queue_people_names = filtered_dict
    except KeyError:
        pass
@dp.callback_query(F.data == "p2")
async def p4(callback: types.CallbackQuery):
    global game_max_players
    game_max_players = 2
    builder = InlineKeyboardBuilder()
    for i in range(2, 7):
        builder.add(types.InlineKeyboardButton(
            text=f"{i}",
            callback_data=f"p{i}")
        )
    builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"),
                types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct"))
    await callback.message.edit_text(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "p3")
async def p4(callback: types.CallbackQuery):
    global game_max_players
    game_max_players = 3
    builder = InlineKeyboardBuilder()
    for i in range(2, 7):
        builder.add(types.InlineKeyboardButton(
            text=f"{i}",
            callback_data=f"p{i}")
        )
    builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"),
                types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct"))
    await callback.message.edit_text(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "p4")
async def p4(callback: types.CallbackQuery):
    global game_max_players
    game_max_players = 4
    builder = InlineKeyboardBuilder()
    for i in range(2, 7):
        builder.add(types.InlineKeyboardButton(
            text=f"{i}",
            callback_data=f"p{i}")
        )
    builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"),
                types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct"))
    await callback.message.edit_text(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "p5")
async def p5(callback: types.CallbackQuery):
    global game_max_players
    game_max_players = 5
    builder = InlineKeyboardBuilder()
    for i in range(2, 7):
        builder.add(types.InlineKeyboardButton(
            text=f"{i}",
            callback_data=f"p{i}")
        )
    builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"),
                types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct"))
    await callback.message.edit_text(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "p6")
async def p6(callback: types.CallbackQuery):
    global game_max_players
    game_max_players = 6
    builder = InlineKeyboardBuilder()
    for i in range(2, 7):
        builder.add(types.InlineKeyboardButton(
            text=f"{i}",
            callback_data=f"p{i}")
        )
    builder.row(types.InlineKeyboardButton(text="Продолжить", callback_data="continue"),
                types.InlineKeyboardButton(text="Удалить лобби", callback_data="distruct"))
    await callback.message.edit_text(f"Настройки\nКоличество игроков: {game_max_players}", reply_markup=builder.as_markup())

@dp.callback_query(F.data =="open")
async def display_rules(callback : types.CallbackQuery):
    try:
        if callback.from_user.first_name == game_master[f'{callback.from_user.id}']:
            await callback.message.delete()

            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(text="Присоединиться",callback_data='id'))
            builder.row(types.InlineKeyboardButton(text="Выйти", callback_data='leave'))
            builder.row(types.InlineKeyboardButton(text="Удалить Лобби", callback_data='distruct'))
            msg = await callback.message.answer(f"Очередь на игру #{g.lobby_id}", reply_markup=builder.as_markup())
            g.create_queue(callback.from_user.id, msg.message_id)
            queue_msg_id = callback.message.message_id
    except KeyError:
        pass

@dp.callback_query(F.data == "leave")
async def leave_lobby(callback : types.CallbackQuery):
    global game_max_players

    if str(callback.message.message_id) in g.queue_id:
            lobby_to_delete = g.queue_id[str(callback.message.message_id)]
    filtered_dict = {}
    for key, value in g.queue_people.items():
        if str(value) != str(lobby_to_delete):
            filtered_dict[key] = value
    g.queue_people = filtered_dict
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Присоединиться",
        callback_data='id')
    )
    builder.row(types.InlineKeyboardButton(text="Выйти", callback_data='leave'))
    builder.row(types.InlineKeyboardButton(text="Удалить Лобби", callback_data='distruct'))
    value_of_players_in_lobby = -1
    k = ""

    for i in g.queue_people_names:
        #await callback.message.answer(f"{g.queue_people_names[i], callback.message.message_id}")
        if str(g.queue_people_names[i]) == str(callback.message.message_id):
            value_of_players_in_lobby += 1
    key = callback.from_user.first_name
    if str(callback.from_user.first_name) in str(g.queue_people_names):
        value = g.queue_people_names.pop(str(callback.from_user.first_name))
    else:
        return 0
    for key, values in g.queue_people_names.items():
        if str(values) == str(callback.message.message_id):
            k += key + ', '

    await callback.answer(text=f"{callback.from_user.first_name} - выходит из лобби!", cache_time=5, show_alert=True)
    await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=value, text=f"Очередь на игру({value_of_players_in_lobby}/{game_max_players}):\n{k}",reply_markup=builder.as_markup())
    #value_of_players_in_lobby = 0
    k = ""
    if value_of_players_in_lobby == 0:
        g.lobby_id -= 1
        if str(callback.from_user.id) in game_master:
            await callback.message.answer(f"{game_master[f'{callback.from_user.id}']} - Удаляет лобби!")
            try:
                g.queue_id.pop(f"{game_master[f'{callback.from_user.id}']}")
            except KeyError:
                pass
            game_master.pop(f"{callback.from_user.id}")
            game_players.clear()
            game_max_players = 4
            await callback.message.delete()
        try:

            if str(callback.message.message_id) in g.queue_id:
                g.queue_id.pop(str(callback.message.message_id))
            filtered_dict = {}
            for key, value in g.queue_people_names.items():
                if str(value) != str(callback.message.message_id):
                    filtered_dict[key] = value
            g.queue_people_names = filtered_dict
        except KeyError:
            pass

@dp.callback_query(F.data == "id")
async def send_message(callback: types.CallbackQuery):
    global id_needed_lobby
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Присоединиться",
        callback_data='id')
    )
    builder.row(types.InlineKeyboardButton(text="Выйти", callback_data='leave'))
    builder.row(types.InlineKeyboardButton(text="Удалить Лобби", callback_data='distruct'))
    id_needed_lobby.clear()
    for i in g.queue_id:
        if i in g.queue_id:
            id_needed_lobby.append(g.queue_id[i])
            id_needed_lobby.append(i)

    value_of_players_in_lobby = 0
    for i in g.queue_people_names:
        if g.queue_people_names[i] == id_needed_lobby[len(id_needed_lobby)-1]:
            value_of_players_in_lobby += 1
    if value_of_players_in_lobby <= game_max_players:
        if (g.add_player(callback.from_user.id, id_needed_lobby[len(id_needed_lobby)-2]) == True):
            g.queue_people_names[f"{callback.from_user.first_name}"] = id_needed_lobby[len(id_needed_lobby) - 1]
            await callback.message.answer(f"{callback.from_user.first_name}, вы встали в очередь на игру")
            value_of_players_in_lobby += 1
        else:
            await callback.message.answer(f"{callback.from_user.first_name}, Вы уже стоите в очереди на игру")
    else:
        await callback.message.answer('Очередь заполнена')
    k = ''
    for key, value in g.queue_people_names.items():
        if value == id_needed_lobby[len(id_needed_lobby)-1]:
            k += key + ', '
    try:
        await bot.edit_message_text(chat_id=callback.message.chat.id,
                                    message_id=id_needed_lobby[len(id_needed_lobby) - 1],
                                    text=f"Очередь на игру({value_of_players_in_lobby}/{game_max_players}):\n{k}",
                                    reply_markup=builder.as_markup())
    except aiogram.exceptions.TelegramBadRequest:
        pass


#KEYBOARD START-----------------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    asyncio.run(main())