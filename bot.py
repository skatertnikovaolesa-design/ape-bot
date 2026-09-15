import asyncio
import random
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
TOKEN = "8647397511:AAFIj9Vf5yqPPC5jq4IbeKji8Igd8ciru48"
ADMIN_IDS = [644972263, 324171335]

# ============ ДАННЫЕ ============
players = {}

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

# ============ ЕДИНАЯ КНОПКА ПОДТВЕРЖДЕНИЯ ============
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

        # Уведомление игроку с фото наклейки
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

# ============ ЖЕРЕБЬЁВКА 50/50 ============
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

    # Роли в личку
    for h in hunters:
        try:
            await bot.send_message(
                h["id"],
                "🔪 <b>Ты — ОХОТНИК!</b>\n"
                "Твоя цель — найти и поймать жертв. Удачи! 🎭",
                parse_mode="HTML"
            )
        except Exception:
            pass

    for v in victims:
        try:
            await bot.send_message(
                v["id"],
                "🏃 <b>Ты — ЖЕРТВА!</b>\n"
                "Беги и прячься от охотников! Удачи! 🎭",
                parse_mode="HTML"
            )
        except Exception:
            pass

@dp.callback_query(F.data == "clear_list")
async def cb_clear(callback: CallbackQuery):
    count = len(players)
    players.clear()
    await callback.message.edit_text(f"🔄 Список очищен. Было игроков: {count}. Готово к новой игре!")

@dp.message(Command("newgame"))
async def newgame(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    count = len(players)
    players.clear()
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