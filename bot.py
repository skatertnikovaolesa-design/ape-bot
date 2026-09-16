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

# ============ НАСТРОЙКИ ============
TOKEN = os.getenv("TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",")]
HUNTERS_CHAT_ID = os.getenv("HUNTERS_CHAT_ID")
VICTIMS_CHAT_ID = os.getenv("VICTIMS_CHAT_ID")

# ============ ДАННЫЕ ============
players = {}
current_round = 0

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ============ СОСТОЯНИЯ ============
class Reg(StatesGroup):
    car = State()
    plate = State()
    team = State()

# ============ МЕНЮ ============
def user_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Регистрация"), KeyboardButton(text="💸 Я оплатил")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Админ-панель")],
            [KeyboardButton(text="📝 Регистрация"), KeyboardButton(text="💸 Я оплатил")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True
    )

# ============ РЕГИСТРАЦИЯ ============
@dp.message(Command("reg"))
async def reg_start(message: Message, state: FSMContext):
    if message.from_user.id in players:
        await message.answer("Ты уже зарегистрирован. Если ошибся — напиши /unreg")
        return
    await message.answer("🚗 Введи марку авто:")
    await state.set_state(Reg.car)

@dp.message(Reg.car)
async def reg_car(message: Message, state: FSMContext):
    await state.update_data(car=message.text)
    await message.answer("🔢 Введи номер авто:")
    await state.set_state(Reg.plate)

@dp.message(Reg.plate)
async def reg_plate(message: Message, state: FSMContext):
    await state.update_data(plate=message.text)
    await message.answer("👥 Введи название команды:")
    await state.set_state(Reg.team)

@dp.message(Reg.team)
async def reg_team(message: Message, state: FSMContext):
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
    }
    await state.clear()
    await message.answer(
        f"✅ Регистрация завершена!\n\n"
        f"🚗 {data['car']} | {data['plate']}\n"
        f"👥 {data['team']}\n\n"
        f"💰 Взнос: 500₽\n"
        f"Оплата наличными или переводом организатору.\n"
        f"После оплаты нажми /pay — админ отметит тебя."
    )

@dp.message(Command("unreg"))
async def unreg(message: Message):
    uid = message.from_user.id
    if uid in players:
        del players[uid]
        await message.answer("🗑 Регистрация удалена. Можешь зарегистрироваться заново: /reg")
    else:
        await message.answer("Ты и так не зарегистрирован.")

@dp.message(Command("pay"))
async def pay(message: Message):
    if message.from_user.id not in players:
        await message.answer("Сначала зарегистрируйся: /reg")
        return
    await message.answer(
        "💸 Принято! Жди, пока админ отметит тебя в панели, "
        "и после этого он выдаст тебе наклейку на машину ✅\n\n"
        "Если ещё не перевёл — оплата наличными или переводом организатору."
    )

# ============ АДМИН-ПАНЕЛЬ ============
@dp.message(Command("panel"))
async def panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Эта команда только для админа.")
        return
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить игрока", callback_data="show_confirm")],
        [InlineKeyboardButton(text="📋 Полный список", callback_data="show_list")],
        [InlineKeyboardButton(text="🎲 Жеребьёвка", callback_data="show_roles")],
        [InlineKeyboardButton(text="📊 Результаты раунда", callback_data="show_rounds")],
        [InlineKeyboardButton(text="📋 Итоги игры", callback_data="show_results")],
        [InlineKeyboardButton(text="🔄 Очистить список", callback_data="clear_list")],
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
        text += f"{status} <b>{p['team']}</b>\n"
        text += f"🚗 {p['car']} | {p['plate']}\n"
        text += f"👤 {p['username']}\n\n"
    await callback.message.edit_text(text, parse_mode="HTML")

# ============ ПОДТВЕРЖДЕНИЕ ============
@dp.callback_query(F.data == "show_confirm")
async def cb_show_confirm(callback: CallbackQuery):
    buttons = []
    for uid, p in players.items():
        if not p.get("confirmed"):
            buttons.append([InlineKeyboardButton(
                text=f"{p['team']} ({p['plate']})",
                callback_data=f"confirm_{uid}"
            )])
    if not buttons:
        await callback.message.edit_text("Все игроки уже подтверждены ✅")
        return
    await callback.message.edit_text(
        "Кто приехал И оплатил? Жми на игрока:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
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
            await bot.send_photo(
                uid,
                photo,
                caption=(
                    "✅ <b>Оплата подтверждена!</b>\n"
                    "Ты отмечен как приехавший и оплативший. Жди жеребьёвку! 🎭\n\n"
                    "📍 Наклейку нужно приклеить в крайний левый бок лобового стекла."
                ),
                parse_mode="HTML"
            )
        except Exception:
            try:
                await bot.send_message(
                    uid,
                    "✅ <b>Оплата подтверждена!</b>\n"
                    "Ты отмечен как приехавший и оплативший. Жди жеребьёвку! 🎭\n\n"
                    "📍 Наклейку нужно приклеить в крайний левый бок лобового стекла.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    await cb_show_confirm(callback)

# ============ ЖЕРЕБЬЁВКА ============
@dp.callback_query(F.data == "show_roles")
async def cb_roles(callback: CallbackQuery):
    ready = [p for p in players.values() if p.get("confirmed")]
    total = len(ready)
    if total < 2:
        await callback.message.edit_text(
            f"Мало подтверждённых игроков: {total}. Нужно минимум 2.\n"
            f"Сначала подтверди их в «✅ Подтвердить игрока»."
        )
        return

    half = total // 2
    if total % 2 == 0:
        hunters_count = half
    else:
        hunters_count = random.choice([half, total - half])

    random.shuffle(ready)
    hunters = ready[:hunters_count]
    victims = ready[hunters_count:]

    for h in hunters:
        players[h["id"]]["role"] = "hunter"
    for v in victims:
        players[v["id"]]["role"] = "victim"

    text = "🎭 <b>Жеребьёвка</b>\n\n"
    text += f"Всего игроков: <b>{total}</b>\n"
    text += f"🔪 Охотники: <b>{len(hunters)}</b>\n"
    text += f"🏃 Жертвы: <b>{len(victims)}</b>\n\n"
    text += "🔪 <b>Охотники:</b>\n"
    for h in hunters:
        text += f"— {h['team']} | {h['plate']}\n"
    text += "\n🏃 <b>Жертвы:</b>\n"
    for v in victims:
        text += f"— {v['team']} | {v['plate']}\n"
    await callback.message.edit_text(text, parse_mode="HTML")

    for h in hunters:
        try:
            link = await bot.create_chat_invite_link(
                chat_id=int(HUNTERS_CHAT_ID),
                member_limit=1
            )
            await bot.send_message(
                h["id"],
                "🔪 <b>Ты — ОХОТНИК!</b>\n"
                "Твоя цель — найти и поймать жертв. Удачи! 🎭\n\n"
                f"👉 Вступай в группу охотников:\n{link.invite_link}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    for v in victims:
        try:
            link = await bot.create_chat_invite_link(
                chat_id=int(VICTIMS_CHAT_ID),
                member_limit=1
            )
            await bot.send_message(
                v["id"],
                "🏃 <b>Ты — ЖЕРТВА!</b>\n"
                "Беги и прячься от охотников! Удачи! 🎭\n\n"
                f"👉 Вступай в группу жертв:\n{link.invite_link}",
                parse_mode="HTML"
            )
        except Exception:
            pass

# ============ РЕЗУЛЬТАТЫ РАУНДОВ ============
@dp.callback_query(F.data == "show_rounds")
async def cb_show_rounds(callback: CallbackQuery):
    if not players:
        await callback.message.edit_text("Список пуст.")
        return
    buttons = [
        [InlineKeyboardButton(text="Раунд 1", callback_data="round_1")],
        [InlineKeyboardButton(text="Раунд 2", callback_data="round_2")],
        [InlineKeyboardButton(text="Раунд 3", callback_data="round_3")],
    ]
    await callback.message.edit_text(
        "📊 Какой раунд заполняем?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@dp.callback_query(F.data.startswith("round_"))
async def cb_select_round(callback: CallbackQuery):
    global current_round
    current_round = int(callback.data.split("_")[1])
    await show_round_players(callback)

async def show_round_players(callback: CallbackQuery):
    buttons = []
    for uid, p in players.items():
        if p.get("confirmed"):
            role_icon = "🔪" if p.get("role") == "hunter" else "🏃" if p.get("role") == "victim" else "❓"
            buttons.append([InlineKeyboardButton(
                text=f"{role_icon} {p['team']} ({p['plate']}) — {p['score']} б.",
                callback_data=f"player_{uid}"
            )])
    if not buttons:
        await callback.message.edit_text("Нет подтверждённых игроков.")
        return
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="show_rounds")])
    await callback.message.edit_text(
        f"📊 <b>Раунд {current_round}</b>\n"
        f"Жми на игрока, чтобы начислить баллы:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("player_"))
async def cb_player_actions(callback: CallbackQuery):
    uid = int(callback.data.split("_")[1])
    if uid not in players:
        await callback.answer("Игрок не найден")
        return
    p = players[uid]

    if current_round in [1, 2]:
        car_points = 2
        hide_points = 3
    else:
        car_points = 4
        hide_points = 6

    buttons = [
        [InlineKeyboardButton(
            text=f"🚗 +1 машина (+{car_points})",
            callback_data=f"add_car_{uid}"
        )],
        [InlineKeyboardButton(
            text=f"🏃 Спрятался (+{hide_points})",
            callback_data=f"add_hide_{uid}"
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"back_round_{current_round}"
        )],
    ]
    await callback.message.edit_text(
        f"<b>{p['team']}</b> | {p['car']} {p['plate']}\n"
        f"Текущие баллы: <b>{p['score']}</b>\n\n"
        f"Что начислить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("add_car_"))
async def cb_add_car(callback: CallbackQuery):
    uid = int(callback.data.split("_")[2])
    if uid in players:
        points = 2 if current_round in [1, 2] else 4
        players[uid]["score"] += points
        await callback.answer(f"+{points} баллов")
    await cb_player_actions(callback)

@dp.callback_query(F.data.startswith("add_hide_"))
async def cb_add_hide(callback: CallbackQuery):
    uid = int(callback.data.split("_")[2])
    if uid in players:
        points = 3 if current_round in [1, 2] else 6
        players[uid]["score"] += points
        await callback.answer(f"+{points} баллов")
    await cb_player_actions(callback)

@dp.callback_query(F.data.startswith("back_round_"))
async def cb_back_round(callback: CallbackQuery):
    await show_round_players(callback)

# ============ ИТОГИ ИГРЫ ============
@dp.callback_query(F.data == "show_results")
async def cb_show_results(callback: CallbackQuery):
    if not players:
        await callback.message.edit_text("Список пуст.")
        return
    sorted_players = sorted(
        [p for p in players.values() if p.get("confirmed")],
        key=lambda x: x["score"],
        reverse=True
    )
    if not sorted_players:
        await callback.message.edit_text("Нет подтверждённых игроков.")
        return

    text = "🏆 <b>Итоги игры</b>\n\n"
    for i, p in enumerate(sorted_players, 1):
        role_icon = "🔪" if p.get("role") == "hunter" else "🏃" if p.get("role") == "victim" else "❓"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {role_icon} <b>{p['team']}</b> — <b>{p['score']}</b> б.\n"
        text += f"   {p['car']} {p['plate']}\n\n"

    await callback.message.edit_text(text, parse_mode="HTML")

# ============ ОЧИСТКА ============
@dp.callback_query(F.data == "clear_list")
async def cb_clear(callback: CallbackQuery):
    global current_round
    count = len(players)
    players.clear()
    current_round = 0
    await callback.message.edit_text(f"🔄 Список очищен. Было игроков: {count}. Готово к новой игре!")

@dp.message(Command("newgame"))
async def newgame(message: Message):
    global current_round
    if message.from_user.id not in ADMIN_IDS:
        return
    count = len(players)
    players.clear()
    current_round = 0
    await message.answer(f"🔄 Список очищен. Было игроков: {count}. Готово к новой игре!")

# ============ КНОПКИ МЕНЮ ============
@dp.message(F.text == "📝 Регистрация")
async def btn_reg(message: Message, state: FSMContext):
    await reg_start(message, state)

@dp.message(F.text == "💸 Я оплатил")
async def btn_pay(message: Message):
    await pay(message)

@dp.message(F.text == "⚙️ Админ-панель")
async def btn_panel(message: Message):
    await panel(message)

@dp.message(F.text == "ℹ️ Помощь")
async def btn_help(message: Message):
    await message.answer(
        "📖 <b>Что умеет бот:</b>\n\n"
        "📝 Регистрация — записаться на игру\n"
        "💸 Я оплатил — сообщить об оплате\n"
        "⚙️ Админ-панель — для организатора\n\n"
        "<b>Команды вручную:</b>\n"
        "/reg — зарегистрироваться\n"
        "/unreg — отменить регистрацию\n"
        "/pay — сообщить об оплате\n"
        "/panel — админ-панель (только для админа)",
        parse_mode="HTML"
    )

# ============ СТАРТ ============
@dp.message(CommandStart())
async def start_handler(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    menu = admin_menu() if is_admin else user_menu()
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        f"Жми на кнопки внизу экрана 👇",
        reply_markup=menu
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
