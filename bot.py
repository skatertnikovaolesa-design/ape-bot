import asyncio
import random
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

# ============ НАСТРОЙКИ ============
TOKEN = os.getenv("TOKEN")
# Три админа (твой, второй и новый)
ADMIN_IDS = [644972263, 324171335, 504642876]

# ВСТРОЕННЫЕ ID БЕСЕД
HUNTERS_CHAT_ID = -1004494212932
VICTIMS_CHAT_ID = -1004426890988
ADMIN_CONTACT = "@pa1_1_1a"

# ПРОКСИ ИЗ CLOUDFLARE
PROXY_URL = "https://plain-lab-e69bape.skatertnikovaolesa.workers.dev"

# ============ ДАННЫЕ ============
players = {}
current_round = 0

# Подключение через прокси
session = AiohttpSession(api=TelegramAPIServer.from_base(PROXY_URL))
bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

# ============ СОСТОЯНИЯ ============
class Reg(StatesGroup):
    car = State()
    plate = State()
    team = State()

class Edit(StatesGroup):
    choosing_field = State()
    new_value = State()

# ============ МЕНЮ ============
def user_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Регистрация"), KeyboardButton(text="💸 Я оплатил")],
            [KeyboardButton(text="✏️ Изменить данные")],
        ],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Админ-панель")],
            [KeyboardButton(text="📝 Регистрация"), KeyboardButton(text="💸 Я оплатил")],
            [KeyboardButton(text="✏️ Изменить данные")],
        ],
        resize_keyboard=True
    )

MENU_BUTTONS = ["📝 Регистрация", "💸 Я оплатил", "✏️ Изменить данные", "ℹ️ Помощь", "⚙️ Админ-панель"]

# ============ РЕГИСТРАЦИЯ ============
@dp.message(Command("reg"))
async def reg_start(message: Message, state: FSMContext):
    if message.from_user.id in players:
        is_admin = message.from_user.id in ADMIN_IDS
        menu = admin_menu() if is_admin else user_menu()
        await message.answer("Ты уже зарегистрирован. Если ошибся — напиши /unreg", reply_markup=menu)
        return
    await message.answer("🚗 Введи марку авто:", reply_markup=user_menu())
    await state.set_state(Reg.car)

@dp.message(Reg.car)
async def reg_car(message: Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        await message.answer("Пожалуйста, введи марку авто текстом:")
        return
    await state.update_data(car=message.text)
    await message.answer("🔢 Введи номер авто:")
    await state.set_state(Reg.plate)

@dp.message(Reg.plate)
async def reg_plate(message: Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        await message.answer("Пожалуйста, введи номер авто текстом:")
        return
    await state.update_data(plate=message.text)
    await message.answer("👥 Введи название команды:")
    await state.set_state(Reg.team)

@dp.message(Reg.team)
async def reg_team(message: Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        await message.answer("Пожалуйста, введи название команды текстом:")
        return
    data = await state.update_data(team=message.text)
    user = message.from_user
    players[user.id] = {
        "id": user.id,
        "name": user.full_name,
        "username": f"@{user.username}" if user.username else "нет ника",
        "car": data["car"],
        "plate": data["plate"],
        "team": data["team"],
        "confirmed": False,
        "score": 0,
        "found": False
    }
    await state.clear()
    is_admin = user.id in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    await message.answer(
        f"✅ Регистрация завершена!\n\n"
        f"🚗 {data['car']} | {data['plate']}\n"
        f"👥 {data['team']}\n\n"
        f"💰 Взнос: 500₽\n"
        f"Оплата только НАЛИЧНЫМИ 500₽.\n"
        f"Если перевод — +2х в цене (1000₽).\n"
        f"После оплаты нажми /pay — админ отметит тебя.\n\n"
        f"⏳ Ждите подтверждения.\n"
        f"Если у вас возникли вопросы — свяжитесь с админом: {ADMIN_CONTACT}",
        reply_markup=menu
    )

@dp.message(Command("unreg"))
async def unreg(message: Message):
    uid = message.from_user.id
    is_admin = uid in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    if uid in players:
        del players[uid]
        await message.answer("🗑 Регистрация удалена. Можешь зарегистрироваться заново: /reg", reply_markup=menu)
    else:
        await message.answer("Ты и так не зарегистрирован.", reply_markup=menu)

@dp.message(Command("pay"))
async def pay(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    if message.from_user.id not in players:
        await message.answer("Сначала зарегистрируйся: /reg", reply_markup=menu)
        return
    await message.answer(
        "💸 Принято! Жди, пока админ отметит тебя в панели, "
        "и после этого он выдаст тебе наклейку на машину ✅",
        reply_markup=menu
    )

# ============ ИЗМЕНЕНИЕ ДАННЫХ ============
@dp.message(Command("edit"))
async def edit_start(message: Message, state: FSMContext):
    is_admin = message.from_user.id in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    if message.from_user.id not in players:
        await message.answer("Сначала зарегистрируйся: /reg", reply_markup=menu)
        return
    buttons = [
        [InlineKeyboardButton(text="🚗 Марка авто", callback_data="edit_car")],
        [InlineKeyboardButton(text="🔢 Номер", callback_data="edit_plate")],
        [InlineKeyboardButton(text="👥 Название команды", callback_data="edit_team")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")],
    ]
    await message.answer("✏️ Что хочешь изменить?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.set_state(Edit.choosing_field)

@dp.callback_query(F.data.startswith("edit_"))
async def edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]
    if field == "cancel":
        await state.clear()
        await callback.message.edit_text("Изменение отменено.")
        return
    field_names = {"car": "марку авто", "plate": "номер", "team": "название команды"}
    await state.update_data(field=field)
    await callback.message.edit_text(f"Введи новое значение для поля «{field_names[field]}»:")
    await state.set_state(Edit.new_value)

@dp.message(Edit.new_value)
async def edit_save(message: Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        await message.answer("Пожалуйста, введи новое значение текстом:")
        return
    data = await state.get_data()
    field = data.get("field")
    uid = message.from_user.id
    is_admin = uid in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    if uid in players:
        players[uid][field] = message.text
        field_names = {"car": "Марка авто", "plate": "Номер", "team": "Команда"}
        await message.answer(f"✅ {field_names[field]} обновлено!\nНовое значение: {message.text}", reply_markup=menu)
    await state.clear()

# ============ АДМИН-ПАНЕЛЬ ============
@dp.message(Command("panel"))
async def panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Эта команда только для админа.", reply_markup=user_menu())
        return
    buttons = [
        [InlineKeyboardButton(text="👥 Игроки", callback_data="show_players")],
        [InlineKeyboardButton(text="📋 Полный список", callback_data="show_list")],
        [InlineKeyboardButton(text="🎲 Жеребьёвка", callback_data="show_roles")],
        [InlineKeyboardButton(text="🔄 Сменить роли (2 раунд)", callback_data="switch_roles")],
        [InlineKeyboardButton(text="🎲 Пережеребьёвка (3 раунд)", callback_data="reshuffle_roles")],
        [InlineKeyboardButton(text="📊 Результаты раунда", callback_data="show_rounds")],
        [InlineKeyboardButton(text="🏁 Итоги игры", callback_data="show_results")],
        [InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_list")],
    ]
    await message.answer("⚙️ Админ-панель:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "show_list")
async def cb_list(callback: CallbackQuery):
    if not players:
        await callback.message.edit_text("Список пуст.")
        return
    text = "📋 <b>Все игроки:</b>\n\n"
    for p in players.values():
        status = "✅" if p.get("confirmed") else "❌"
        text += f"{status} <b>🚗 {p['car']} | {p['plate']}</b>\n"
        text += f"👥 {p['team']} | 👤 {p['username']}\n\n"
    await callback.message.edit_text(text, parse_mode="HTML")

# ============ ИГРОКИ ============
@dp.callback_query(F.data == "show_players")
async def cb_show_players(callback: CallbackQuery):
    if not players:
        await callback.message.edit_text("Список пуст.")
        return
    buttons = []
    for uid, p in players.items():
        status = "✅" if p.get("confirmed") else "❌"
        buttons.append([InlineKeyboardButton(text=f"{status} 🚗 {p['plate']} ({p['team']})", callback_data=f"player_card_{uid}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_panel")])
    await callback.message.edit_text("👥 <b>Игроки</b>\nЖми на игрока для действий:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data.startswith("player_card_"))
async def cb_player_card(callback: CallbackQuery):
    uid = int(callback.data.split("_")[2])
    if uid not in players:
        await callback.answer("Игрок не найден")
        return
    p = players[uid]
    status = "✅ Подтверждён" if p.get("confirmed") else "❌ Не подтверждён"
    buttons = []
    if p.get("confirmed"):
        buttons.append([InlineKeyboardButton(text="❌ Отменить подтверждение", callback_data=f"unconfirm_{uid}")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{uid}")])
    
    buttons.append([InlineKeyboardButton(text="🚪 Игрок вышел", callback_data=f"exit_{uid}")])
    buttons.append([InlineKeyboardButton(text="🗑 Удалить из базы", callback_data=f"delete_{uid}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="show_players")])
    
    await callback.message.edit_text(
        f"🚗 <b>{p['car']} | {p['plate']}</b>\n"
        f"👥 {p['team']}\n"
        f"👤 {p['username']}\n"
        f"Статус: {status}\n"
        f"🏆 Баллы: {p.get('score', 0)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("confirm_"))
async def cb_confirm(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    if uid in players:
        players[uid]["confirmed"] = True
        name = players[uid]["name"]
        await callback.answer(f"✅ {name} подтверждён")
        try:
            photo = FSInputFile("nakleyka.jpg")
            await bot.send_photo(uid, photo, caption="✅ <b>Оплата подтверждена!</b>\nТы отмечен как приехавший и оплативший. Жди жеребьёвку! 🎭\n\n📍 Наклейку нужно приклеить в крайний левый бок лобового стекла.", parse_mode="HTML")
        except Exception:
            try:
                await bot.send_message(uid, "✅ <b>Оплата подтверждена!</b>\nТы отмечен как приехавший и оплативший. Жди жеребьёвку! 🎭\n\n📍 Наклейку нужно приклеить в крайний левый бок лобового стекла.", parse_mode="HTML")
            except Exception:
                pass
    await cb_player_card(callback)

@dp.callback_query(F.data.startswith("unconfirm_"))
async def cb_unconfirm(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    if uid in players:
        players[uid]["confirmed"] = False
        await callback.answer(f"❌ {players[uid]['name']} снят с подтверждения")
    await cb_player_card(callback)

@dp.callback_query(F.data.startswith("exit_"))
async def cb_exit_player(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    if uid in players:
        name = players[uid]["name"]
        try:
            await bot.ban_chat_member(chat_id=HUNTERS_CHAT_ID, user_id=uid)
            await bot.unban_chat_member(chat_id=HUNTERS_CHAT_ID, user_id=uid)
        except Exception: pass
        try:
            await bot.ban_chat_member(chat_id=VICTIMS_CHAT_ID, user_id=uid)
            await bot.unban_chat_member(chat_id=VICTIMS_CHAT_ID, user_id=uid)
        except Exception: pass
        del players[uid]
        await callback.answer(f"🚪 {name} удалён из игры")
    await cb_show_players(callback)

@dp.callback_query(F.data.startswith("delete_"))
async def cb_delete(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    if uid in players:
        name = players[uid]["name"]
        del players[uid]
        await callback.answer(f"🗑 {name} удалён из базы")
    await cb_show_players(callback)

@dp.callback_query(F.data == "back_panel")
async def cb_back_panel(callback: CallbackQuery):
    buttons = [
        [InlineKeyboardButton(text="👥 Игроки", callback_data="show_players")],
        [InlineKeyboardButton(text="📋 Полный список", callback_data="show_list")],
        [InlineKeyboardButton(text="🎲 Жеребьёвка", callback_data="show_roles")],
        [InlineKeyboardButton(text="🔄 Сменить роли (2 раунд)", callback_data="switch_roles")],
        [InlineKeyboardButton(text="🎲 Пережеребьёвка (3 раунд)", callback_data="reshuffle_roles")],
        [InlineKeyboardButton(text="📊 Результаты раунда", callback_data="show_rounds")],
        [InlineKeyboardButton(text="🏁 Итоги игры", callback_data="show_results")],
        [InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_list")],
    ]
    await callback.message.edit_text("⚙️ Админ-панель:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ============ ЖЕРЕБЬЁВКА И РАУНДЫ ============
async def revoke_old_links():
    for uid, p in players.items():
        if "last_link" in p:
            try:
                chat_id = HUNTERS_CHAT_ID if p.get("role") == "hunter" else VICTIMS_CHAT_ID
                await bot.revoke_chat_invite_link(chat_id=chat_id, invite_link=p["last_link"])
                del p["last_link"]
            except Exception:
                pass

async def send_links(hunters, victims):
    for h in hunters:
        try:
            link = await bot.create_chat_invite_link(chat_id=HUNTERS_CHAT_ID, member_limit=1)
            players[h["id"]]["last_link"] = link.invite_link
            await bot.send_message(h["id"], f"🔪 <b>Ты — ОХОТНИК!</b>\nТвоя цель — найти и поймать жертв. Удачи! 🎭\n\n👉 Вступай в группу охотников:\n{link.invite_link}", parse_mode="HTML")
        except Exception: pass
    for v in victims:
        try:
            link = await bot.create_chat_invite_link(chat_id=VICTIMS_CHAT_ID, member_limit=1)
            players[v["id"]]["last_link"] = link.invite_link
            await bot.send_message(v["id"], f"🏃 <b>Ты — ЖЕРТВА!</b>\nБеги и прячься от охотников! Удачи! 🎭\n\n👉 Вступай в группу жертв:\n{link.invite_link}", parse_mode="HTML")
        except Exception: pass

async def kick_all():
    kicked = 0
    for uid in list(players.keys()):
        if uid in ADMIN_IDS: continue
        try:
            await bot.ban_chat_member(chat_id=HUNTERS_CHAT_ID, user_id=uid)
            await bot.unban_chat_member(chat_id=HUNTERS_CHAT_ID, user_id=uid)
            kicked += 1
        except Exception: pass
        try:
            await bot.ban_chat_member(chat_id=VICTIMS_CHAT_ID, user_id=uid)
            await bot.unban_chat_member(chat_id=VICTIMS_CHAT_ID, user_id=uid)
        except Exception: pass
    return kicked

@dp.callback_query(F.data == "show_roles")
async def cb_roles(callback: CallbackQuery):
    ready = [p for p in players.values() if p.get("confirmed")]
    total = len(ready)
    if total < 2:
        await callback.message.edit_text(f"Мало подтверждённых игроков: {total}. Нужно минимум 2.")
        return
    half = total // 2
    hunters_count = half if total % 2 == 0 else random.choice([half, total - half])
    random.shuffle(ready)
    hunters, victims = ready[:hunters_count], ready[hunters_count:]
    for h in hunters: players[h["id"]]["role"] = "hunter"
    for v in victims: players[v["id"]]["role"] = "victim"
    text = f"🎭 <b>Жеребьёвка (1 раунд)</b>\n\nВсего: {total}\n🔪 Охотники: {len(hunters)}\n🏃 Жертвы: {len(victims)}\n\n"
    await callback.message.edit_text(text, parse_mode="HTML")
    await send_links(hunters, victims)

@dp.callback_query(F.data == "switch_roles")
async def cb_switch_roles(callback: CallbackQuery):
    for p in players.values(): p["found"] = False
    await revoke_old_links()
    kicked = await kick_all()
    ready = [p for p in players.values() if p.get("confirmed")]
    if len(ready) < 2:
        await callback.message.edit_text("Мало подтверждённых игроков.")
        return
    hunters, victims = [], []
    for p in ready:
        if p.get("role") == "hunter":
            p["role"] = "victim"
            victims.append(p)
        else:
            p["role"] = "hunter"
            hunters.append(p)
    await send_links(hunters, victims)
    await callback.message.edit_text(f"🔄 <b>Смена ролей (2 раунд)</b>\n\nКикнуто: {kicked}\nРоли поменялись местами.\nСтарые ссылки аннулированы.\nНовые ссылки отправлены.", parse_mode="HTML")

@dp.callback_query(F.data == "reshuffle_roles")
async def cb_reshuffle_roles(callback: CallbackQuery):
    for p in players.values(): p["found"] = False
    await revoke_old_links()
    kicked = await kick_all()
    ready = [p for p in players.values() if p.get("confirmed")]
    if len(ready) < 2:
        await callback.message.edit_text("Мало подтверждённых игроков.")
        return
    half = len(ready) // 2
    hunters_count = half if len(ready) % 2 == 0 else random.choice([half, len(ready) - half])
    random.shuffle(ready)
    hunters, victims = ready[:hunters_count], ready[hunters_count:]
    for h in hunters: players[h["id"]]["role"] = "hunter"
    for v in victims: players[v["id"]]["role"] = "victim"
    await send_links(hunters, victims)
    await callback.message.edit_text(f"🎲 <b>Пережеребьёвка (3 раунд)</b>\n\nКикнуто: {kicked}\nРоли перемешаны заново.\nСтарые ссылки аннулированы.\nНовые ссылки отправлены.", parse_mode="HTML")

# ============ РЕЗУЛЬТАТЫ И БАЛЛЫ ============
@dp.callback_query(F.data == "show_rounds")
async def cb_show_rounds(callback: CallbackQuery):
    buttons = [
        [InlineKeyboardButton(text="Раунд 1", callback_data="round_1")],
        [InlineKeyboardButton(text="Раунд 2", callback_data="round_2")],
        [InlineKeyboardButton(text="Раунд 3", callback_data="round_3")],
    ]
    await callback.message.edit_text("📊 Какой раунд заполняем?", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("round_"))
async def cb_select_round(callback: CallbackQuery):
    global current_round
    current_round = int(callback.data.split("_")[1])
    await show_round_players(callback)

async def show_round_players(callback: CallbackQuery):
    if current_round == 1:
        for p in players.values(): p["found"] = False

    hunters = [p for p in players.values() if p.get("confirmed") and p.get("role") == "hunter"]
    victims = [p for p in players.values() if p.get("confirmed") and p.get("role") == "victim"]
    
    if not hunters and not victims:
        await callback.message.edit_text("Нет подтверждённых игроков с ролями.")
        return

    buttons = []
    text = f"📊 <b>Раунд {current_round}</b>\n\n"
    
    for h in hunters:
        text += f"🔪 {h['car']} {h['plate']} | {h['team']} — {h['score']} б.\n"
        buttons.append([InlineKeyboardButton(text=f"🔪 {h['car']} {h['plate']} | {h['team']} — {h['score']} б.", callback_data=f"player_{h['id']}")])
    
    text += "\n"
    for v in victims:
        status = "✅ Найден " if v.get("found") else ""
        text += f"{status}{v['car']} {v['plate']} | {v['team']} — {v['score']} б.\n"
        buttons.append([InlineKeyboardButton(text=f"{status}{v['car']} {v['plate']} | {v['team']} — {v['score']} б.", callback_data=f"player_{v['id']}")])

    buttons.append([InlineKeyboardButton(text="🏁 Завершить раунд", callback_data="finish_round")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_panel")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data.startswith("player_"))
async def cb_player_actions(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    if uid not in players: return
    p = players[uid]
    
    points_car = 2 if current_round in [1, 2] else 4
    points_hide = 3 if current_round in [1, 2] else 6

    buttons = []
    if p.get("role") == "hunter":
        buttons.append([InlineKeyboardButton(text=f"🚗 +1 машина (+{points_car})", callback_data=f"add_car_{uid}")])
    else:
        buttons.append([InlineKeyboardButton(text=f"🏃 + Спрятался (+{points_hide})", callback_data=f"add_hide_{uid}")])
        buttons.append([InlineKeyboardButton(text=f"❌ Отметить как найденного", callback_data=f"mark_found_{uid}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_round_{current_round}")])
    
    # Убрали статус "Прячется" из карточки
    status_text = "✅ Найден" if p.get("found") else "В игре"
    
    await callback.message.edit_text(
        f"🚗 <b>{p['car']} | {p['plate']}</b>\n"
        f"👥 {p['team']}\n"
        f"Роль: {'🔪 Охотник' if p['role']=='hunter' else '🏃 Жертва'}\n"
        f"Баллы: {p['score']}\n"
        f"Статус: {status_text if p['role']=='victim' else '-'}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("add_car_"))
async def cb_add_car(callback: CallbackQuery):
    uid = int(callback.data.split("_")[2])
    points = 2 if current_round in [1, 2] else 4
    if uid in players:
        players[uid]["score"] += points
        await callback.answer(f"+{points} баллов")
    await cb_player_actions(callback)

@dp.callback_query(F.data.startswith("add_hide_"))
async def cb_add_hide(callback: CallbackQuery):
    uid = int(callback.data.split("_")[2])
    points = 3 if current_round in [1, 2] else 6
    if uid in players:
        players[uid]["score"] += points
        await callback.answer(f"+{points} баллов")
    await cb_player_actions(callback)

@dp.callback_query(F.data.startswith("mark_found_"))
async def cb_mark_found(callback: CallbackQuery):
    uid = int(callback.data.split("_")[2])
    if uid in players:
        players[uid]["found"] = True
        await callback.answer("✅ Отмечен как найденный")
    await cb_player_actions(callback)

@dp.callback_query(F.data.startswith("back_round_"))
async def cb_back_round(callback: CallbackQuery):
    await show_round_players(callback)

@dp.callback_query(F.data == "finish_round")
async def cb_finish_round(callback: CallbackQuery):
    points_hide = 3 if current_round in [1, 2] else 6
    count = 0
    found_names = []
    
    for p in players.values():
        if p.get("confirmed") and p.get("role") == "victim":
            if not p.get("found", False):
                p["score"] += points_hide
                count += 1
            else:
                found_names.append(p['team'])

    text = f"🏁 <b>Раунд {current_round} завершён!</b>\n\n"
    text += f"Бот начислил +{points_hide} баллов {count} жертвам, которых не нашли.\n\n"
    if found_names:
        text += f"✅ <b>Были найдены:</b> {', '.join(found_names)}"
        
    await callback.message.edit_text(text, parse_mode="HTML")

# ============ ИТОГИ ============
@dp.callback_query(F.data == "show_results")
async def cb_show_results(callback: CallbackQuery):
    sorted_players = sorted([p for p in players.values() if p.get("confirmed")], key=lambda x: x["score"], reverse=True)
    if not sorted_players:
        await callback.message.edit_text("Нет подтверждённых игроков.")
        return
    text = "🏆 <b>Итоги игры</b>\n\n"
    for i, p in enumerate(sorted_players, 1):
        role_icon = "🔪" if p.get("role") == "hunter" else "🏃" if p.get("role") == "victim" else "❓"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {role_icon} <b>{p['team']}</b> — <b>{p['score']}</b> б.\n   🚗 {p['car']} {p['plate']}\n\n"
    await callback.message.edit_text(text, parse_mode="HTML")

@dp.callback_query(F.data == "clear_list")
async def cb_clear(callback: CallbackQuery):
    global current_round
    count = len(players)
    players.clear()
    current_round = 0
    await callback.message.edit_text(f"🗑 Список очищен. Было игроков: {count}. Готово к новой игре!")

# ============ КНОПКИ МЕНЮ ============
@dp.message(F.text == "📝 Регистрация")
async def btn_reg(message: Message, state: FSMContext):
    await reg_start(message, state)

@dp.message(F.text == "💸 Я оплатил")
async def btn_pay(message: Message):
    await pay(message)

@dp.message(F.text == "✏️ Изменить данные")
async def btn_edit(message: Message, state: FSMContext):
    await edit_start(message, state)

@dp.message(F.text == "⚙️ Админ-панель")
async def btn_panel(message: Message):
    await panel(message)

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    await message.answer("Меню:", reply_markup=menu)

# ============ СТАРТ ============
@dp.message(CommandStart())
async def start_handler(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    await message.answer(f"Привет, {message.from_user.full_name}! 👋\n\nЖми на кнопки внизу экрана 👇", reply_markup=menu)

async def main():
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
