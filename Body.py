import asyncio
import logging
import sys
import time

import aiogram.exceptions
import aiogram
from os import getenv

from aiogram.fsm.storage.base import StorageKey
from config import TOKEN
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.markdown import hbold
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from random import randint
#Машина состояний
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import utils.states as s
from keyboards import kb
from game import game_states as gs


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

storage = MemoryStorage()

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=storage)

async def main():

    await dp.start_polling(bot, skip_updates=True)


class Player():
    def __init__(self, p_id, p_name, dice_amount, dice_value):
        self.p_id = p_id #player id
        self.p_name = p_name #player tg name
        self.dice_amount = dice_amount
        self.dice_value = dice_value #contain diece values
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
class Session():
    def __init__(self, lobby_id, player_name,player_id,chat_id, players):
        self.lobby_id = lobby_id
        self.player_name = player_name
        self.player_id = player_id
        self.turn_order = []
        self.turn_order_ids = []
        self.current_turn = 0
        self.chat_id = chat_id
        self.current_bet = 0
        self.players : Player = players
        self.dice_stickers = [
            "CAACAgIAAxkBAAEDQ0dlvyjVqzlFoF5eEKv8soiwFmJQgQACx0IAApz5-EmsuMzL_y9kZTQE",
            "CAACAgIAAxkBAAEDQ0llvyjYFOLzPFVj_g_pRtuqoHxgYwACBkYAAnLw-UlniV4oA3b8lDQE",
            "CAACAgIAAxkBAAEDQ0tlvyjZLgOSE7UQ9tUtuKck25DF0AACfTkAAltB-EkDYkBoIWFFkDQE",
            "CAACAgIAAxkBAAEDQ01lvyjbFUVTRyMpEDxkKgF2EPa3nAAC-DwAAmdo-Um3xGOLFpHgGDQE",
            "CAACAgIAAxkBAAEDQ09lvyjch_py0eqblrOCtaznCqZmjAACRDsAAqfy-UmzeOvOrHtInDQE",
            "CAACAgIAAxkBAAEDQ1FlvyjdoNAKnhr9v95EAspKYqbk-QACAT0AAtoeAUqBpmakpJ4VFjQE"
        ]
    async def int_into_emoji(self, p : Player):
        c_id = p.p_id

        dices = p.dice_value
        await bot.send_message(chat_id= c_id, text=f"Ваши кости: {dices}")
        time.sleep(1)
        for i in dices:
            if i == 1:
                await bot.send_sticker(chat_id= c_id, sticker=self.dice_stickers[0])
            elif i == 2:
                await bot.send_sticker(chat_id= c_id,sticker=self.dice_stickers[1])
            elif i == 3:
                await bot.send_sticker(chat_id= c_id,sticker=self.dice_stickers[2])
            elif i == 4:
                await bot.send_sticker(chat_id= c_id,sticker=self.dice_stickers[3])
            elif i == 5:
                await bot.send_sticker(chat_id= c_id,sticker=self.dice_stickers[4])
            else:
                await bot.send_sticker(chat_id= c_id,sticker=self.dice_stickers[5])
        await bot.send_message(chat_id=c_id, text=f"Ваши кости: {dices}")

    async def start_game(self, p : Player):
        self.turn_order = []
        incounter = 0
        for i in range(len(self.player_name)):
            self.turn_order.append(p[i].p_name)
        for i in range(len(self.player_id)):
            self.turn_order_ids.append(p[i].p_id)
        for i in p:
            await self.int_into_emoji(i)

    def c_p_t(self):
        if self.current_turn == len(self.turn_order) or self.current_turn == 0:
            self.current_turn = 0
        else:
            self.current_turn += 1
        return self.current_turn

    async def game(self, callback: types.CallbackQuery, state: FSMContext):
        current_person = ""
        current_bet = []
        for i, name in enumerate(self.turn_order):
            if i == 0:
                current_person = f"{name}";
                await gs.turn_message(callback, self.turn_order, current_person)
                await state.set_state(s.Turn.state_list[0])
            if i != 0:
                current_person = f"{name}"

sessions = []

g = Game()
#Gamebeggin

async def c_s(message: Message, s): #current_session
    for i in s:
        if message.from_user.first_name in i.player_name:
            return i
@dp.message(F.text.lower() == "/startgame")
async def game_beggin(message : Message,  state: FSMContext):
    #проверка, является ли человек участником последнего лобби и является ли он создателем этого лобби.
    if f"{message.from_user.id}" in sessions[len(sessions)-1].player_id and str(message.from_user.id) in game_master:
        current_sesson = await c_s(message, sessions)
        turn_order = current_sesson.turn_order
        current_person = turn_order[current_sesson.c_p_t()]
        next_person_id = ""
        next_person_name = ""
        for count, value in enumerate(current_sesson.turn_order_ids):
            if str(value) == str(message.from_user.id):
                if count != len(current_sesson.turn_order_ids) - 1:
                    next_person_id = int(current_sesson.turn_order_ids[count + 1])
                    next_person_name = current_sesson.turn_order[count + 1]
                else:
                    next_person_id = int(current_sesson.turn_order_ids[0])
                    next_person_name = current_sesson.turn_order[0]

        state_with: FSMContext = FSMContext(
            storage=dp.storage,
            key=StorageKey(
                chat_id=current_sesson.chat_id,  # если юзер в ЛС, то chat_id=user_id
                user_id=next_person_id,
                bot_id=bot.id))
        if str(current_person) == str(message.from_user.first_name):
            await message.answer(f"Ходит: {current_sesson.turn_order[current_sesson.current_turn]}\r\nCделайте ставку, введя две цифры, где:\r\nПервая - Номинал\r\nВторая - Количество")
            await state.set_state(s.Turn.israise)

        else:
            await message.answer(f"Ходит: {current_sesson.turn_order[current_sesson.current_turn]}")
            await state.set_state(None)
            await state_with.set_state(s.Turn.israise)



@dp.message(s.Turn.israise)
async def raise_state(message: Message, state: FSMContext):
    text = message.text
    current_sesson = await c_s(message, sessions)
    turn_order = current_sesson.turn_order
    current_person = turn_order[current_sesson.c_p_t()]
    if gs.string_to_format(text):
        bet = gs.string_to_format(text)[1]
        current_sesson.current_bet = int(bet)
        value = gs.bet_to_format(bet)
        amount = bet[1]
        await message.answer(f"{current_person}, ваша ставка, что на столе:\r\n{value}: {amount} шт.")
        await state.update_data(bet=text,currnet_person=current_person) # пример {'israise': '12'} 12 это ставка
        current_sesson.c_p_t()
        current_person = turn_order[current_sesson.current_turn]
        next_person_id = ""
        next_person_name = ""
        for count, value in enumerate(current_sesson.turn_order_ids):
            if str(value) == str(message.from_user.id):
                if count != len(current_sesson.turn_order_ids)-1:
                    next_person_id = int(current_sesson.turn_order_ids[count+1])
                    next_person_name = current_sesson.turn_order[count+1]
                else:
                    next_person_id = int(current_sesson.turn_order_ids[0])
                    next_person_name = current_sesson.turn_order[0]
        state_with: FSMContext = FSMContext(
            storage=dp.storage,
            key=StorageKey(
                chat_id=current_sesson.chat_id,  # если юзер в ЛС, то chat_id=user_id
                user_id=next_person_id,
                bot_id=bot.id))
        await state_with.set_state(s.Turn.raise_or_open)
        await state.set_state(None)
        await message.answer(f"Ходит: {next_person_name}\r\nТекущая ставка: {current_sesson.current_bet}\r\nСделайте ставку, если вы согласны или напишите 'нет'")
    else:
        await message.delete()
        await message.answer("Ошибка ввода")
        await raise_state(message, state, current_person)

@dp.message(s.Turn.raise_or_open)
async def roo(message : Message, state : FSMContext):
    text = message.text
    current_sesson = await c_s(message, sessions)
    turn_order = current_sesson.turn_order
    current_person = message.from_user.first_name

    bet = str(current_sesson.current_bet)

    b1 = int(bet[0])  # номинал прошлой ставки
    b2 = int(bet[1])  # значение прошлой ставки
    if text.lower() == 'нет' or text.lower() == 'не cогласен' or text.lower() == 'не':
        await message.answer(f"{current_person} - не согласен со ставкой! Вскрываемся.")
        summary_dices_amount = 0
        summary_dices_value = []
        for player in current_sesson.players:
            summary_dices_amount += player.dice_amount
            summary_dices_value += player.dice_value
            await message.answer(f"{player.p_name}:\r\nКоличество костей: {player.dice_amount}\r\nНоминалы костей: {player.dice_value}")
        count_of_amount = 0
        for i in summary_dices_value:
            if str(i) == str(b1):
                count_of_amount+=1
        previos_person = ""
        index = current_sesson.turn_order.index(message.from_user.first_name)
        if index != 0:
            previos_person = current_sesson.turn_order[index-1]
        else:
            previos_person = current_sesson.turn_order[len(current_sesson.turn_order)-1]
        if int(count_of_amount) < int(summary_dices_amount):
            await message.answer(f"Победил - {message.from_user.first_name}\r\n{previos_person} - теряет одну кость.")
        else:
            await message.answer(f"Победил - {previos_person}\r\n{message.from_user.first_name} - теряет одну кость.")
    else:
            if gs.string_to_format(text):
                text = str(gs.string_to_format(text)[1])
                t1 = int(text[0])  # номинал текущей ставки
                t2 = int(text[1])  # значение текущей ставки
                if (((t1 > b1 and b1 != 1) or t1 == 1) and t2 == b2) or (t1 == b1 and t2 > b2):
                    # первое число ставки больше прошлого первого числа ИЛИ второе число ставки больше прошлого второго числа
                    # при этом если ввести 1, а в прошлой ставке было 6, то все ок!
                    bet = gs.string_to_format(text)[1]
                    current_sesson.current_bet = int(bet)
                    value = gs.bet_to_format(bet)
                    amount = bet[1]
                    await message.answer(f"{current_person}, ваша ставка, что на столе:\r\n{value}: {amount} шт.")
                    current_person = turn_order[current_sesson.c_p_t()]
                    await state.update_data(bet=text, currnet_person=current_person)
                    current_sesson.c_p_t()
                    current_person = turn_order[current_sesson.current_turn]
                    next_person_id = ""
                    next_person_name = ""
                    for count, value in enumerate(current_sesson.turn_order_ids):
                        if str(value) == str(message.from_user.id):
                            if count != len(current_sesson.turn_order_ids)-1:
                                next_person_id = int(current_sesson.turn_order_ids[count + 1])
                                next_person_name = current_sesson.turn_order[count + 1]
                            else:
                                next_person_id = int(current_sesson.turn_order_ids[0])
                                next_person_name = current_sesson.turn_order[0]
                    state_with: FSMContext = FSMContext(
                        storage=dp.storage,
                        key=StorageKey(
                            chat_id=current_sesson.chat_id,  # если юзер в ЛС, то chat_id=user_id
                            user_id=next_person_id,
                            bot_id=bot.id))
                    await state_with.set_state(s.Turn.raise_or_open)
                    await state.set_state(None)
                    await message.answer(
                        f"Ходит: {next_person_name}\r\nТекущая ставка: {current_sesson.current_bet}\r\nСделайте ставку, если вы согласны или напишите 'нет'")
                else:
                    await message.delete()
                    await message.answer("Вы можете только повышать ставку!")
            else:
                await message.delete()
                await message.answer("Ошибка ввода")

###########

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


@dp.callback_query(F.data == "continue")
async def continue_game(callback : types.CallbackQuery):
    global game_master

    if str(callback.from_user.id) in game_master:
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
    global game_master

    if str(callback.from_user.id) in game_master:
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
    global game_master

    if str(callback.from_user.id) in game_master:
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
    global game_master

    if str(callback.from_user.id) in game_master:
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
    global game_master

    if str(callback.from_user.id) in game_master:
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
    global game_master

    if str(callback.from_user.id) in game_master:
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
async def send_message(callback: types.CallbackQuery, state : FSMContext):
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
    if value_of_players_in_lobby < game_max_players:
        if (g.add_player(callback.from_user.id, id_needed_lobby[len(id_needed_lobby)-2]) == True):
            g.queue_people_names[f"{callback.from_user.first_name}"] = id_needed_lobby[len(id_needed_lobby) - 1]
            await callback.message.answer(f"{callback.from_user.first_name}, вы встали в очередь на игру")
            value_of_players_in_lobby += 1
        else:
            await callback.message.answer(f"{callback.from_user.first_name}, Вы уже стоите в очереди на игру")
    k = ''
    for key, value in g.queue_people_names.items():
        if value == id_needed_lobby[len(id_needed_lobby) - 1]:
            k += key + ', '
    try:
        await bot.edit_message_text(chat_id=callback.message.chat.id,
                                    message_id=id_needed_lobby[len(id_needed_lobby) - 1],
                                    text=f"Очередь на игру({value_of_players_in_lobby}/{game_max_players}):\n{k}",
                                    reply_markup=builder.as_markup())
    except aiogram.exceptions.TelegramBadRequest:
        pass
    if value_of_players_in_lobby == game_max_players:
        #await callback.message.answer('Начинаем')

        #Начало сессии
        player_names = []
        player_ids = []
        chat_id = callback.message.chat.id

        #Заполнение всех имен пользваотелей
        for key, value in g.queue_people_names.items():
            if str(value) == str(callback.message.message_id):
                player_names.append(key)
        # Заполнение всех ID пользваотелей
        for key, value in g.queue_people.items():
            if str(value) == str(id_needed_lobby[len(id_needed_lobby)-2]):
                player_ids.append(key)

        # Заполнение Данных о пользователе в экземпляры Players
        players = []
        for i in range(len(player_names)):
            random_value = []
            for j in range(5):
                random_value.append(randint(1, 6))
            players.append(Player(player_ids[i], player_names[i], 5, random_value))

        #Создание сессии со всеми данными о пользователях
        sessions.append(Session(id_needed_lobby[len(id_needed_lobby)-2], player_names, player_ids, chat_id, players=players))
        chat_id = callback.message.chat.id

        # Запуск игры
        #Запуск последней созданной сессии и заполнение очереди в start_game и отправка в лс костей для игры
        await sessions[len(sessions)-1].start_game(players)
        await callback.message.answer(f"{callback.from_user.first_name}, для начала игры введите /startgame")

        #очистка пользователей
        players = []
        await callback.message.delete()







#KEYBOARD START-----------------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    asyncio.run(main())