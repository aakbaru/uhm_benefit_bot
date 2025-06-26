
# -*- coding: utf-8 -*-
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
@dp.message_handler(commands=["start"])
async def start(msg: types.Message, state: FSMContext):
    await state.finish()  # Завершить все предыдущие состояния (например, калькулятор)
    lang_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    lang_kb.add("🇷🇺 Русский", "🇺🇿 O‘zbekcha")
    await msg.answer("🇷🇺 Выберите язык / 🇺🇿 Tilni tanlang", reply_markup=lang_kb)
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import logging
import json
from aiogram import Bot
import asyncio

async def drop_pending_updates(bot: Bot):
    await bot.get_updates(offset=-1)
import os
API_TOKEN = os.getenv("BOT_TOKEN")


TEXTS = {
    "ru": texts_ru,
    "uz": texts_uz
}


bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

user_lang = {}
with open("texts_ru.json", encoding="utf-8") as f: TEXTS_RU = json.load(f)
with open("texts_uz.json", encoding="utf-8") as f: TEXTS_UZ = json.load(f)
with open("models.json", encoding="utf-8") as f: MODELS = json.load(f)

def get_text(uid, key):
    lang = user_lang.get(uid, "ru")
    return TEXTS.get(lang, {}).get(key, "❓")
def get_menu(uid):
    lang = user_lang.get(uid, "ru")
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for btn in TEXTS.get(lang, {}).get("menu", []):
        kb.add(KeyboardButton(btn))
    return kb

class CalcForm(StatesGroup):
    model = State()
    hours_per_day = State()
    days_per_month = State()
    months_total = State()
    rent_per_month = State()
    operator_salary = State()
    fuel_per_day = State()
    fuel_price = State()
    service_cost = State()

    

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    lang_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    lang_kb.add("🇷🇺 Русский", "🇺🇿 O‘zbekcha")
    await msg.answer("🇷🇺 Выберите язык / 🇺🇿 Tilni tanlang", reply_markup=lang_kb)




@dp.message_handler(lambda m: m.text.startswith("📞"))
async def contact(msg: types.Message):
    await msg.answer("Менеджер: @UHMLT\nТелефон: +998 90 977 31 35")

@dp.message_handler(lambda m: m.text.startswith("🔒"))
async def policy(msg: types.Message):
    await msg.answer(
        "🔐 Политика конфиденциальности:\n"
        "📄 Документ: https://uhmlandtech.uz/\n"
        "📸 Instagram: https://www.instagram.com/uhm.uz\n"
        "📘 Facebook: https://www.facebook.com/uhmtashkent\n"
        "📢 Telegram-канал: https://t.me/uhmuz"
    )


@dp.message_handler(lambda m: m.text == get_text(m.from_user.id, "catalog"))
async def catalog(msg: types.Message):
    uid = msg.from_user.id
    if uid not in user_lang:
        await msg.answer("Сначала выберите язык.")
        return

    cat_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in MODELS:
        cat_kb.add(KeyboardButton(cat))
    cat_kb.add(KeyboardButton(get_text(uid, "back")))

    await msg.answer(get_text(uid, "choose_category"), reply_markup=cat_kb)




@dp.message_handler(lambda m: m.text in MODELS)
async def show_models_by_category(msg: types.Message):
    uid = msg.from_user.id
    cat = msg.text
    items = MODELS[cat]

    for item in items:
        caption = f"{item['name']} — {item['price']} сум"
        if "specs" in item:
            for k, v in item["specs"].items():
                caption += f"\n• {k}: {v}"
        try:
            await bot.send_photo(msg.chat.id, item["image"], caption=caption)
        except:
            await msg.answer(caption)

    await msg.answer("⬅ Вернуться в меню", reply_markup=get_menu(uid))



@dp.message_handler(lambda m: m.text in ["🇷🇺 Русский", "🇺🇿 O‘zbekcha"])
async def set_lang(msg: types.Message):
    user_lang[msg.from_user.id] = "ru" if "Рус" in msg.text else "uz"
    await msg.answer(get_text(msg.from_user.id, "start"), reply_markup=get_menu(msg.from_user.id))


@dp.message_handler(lambda m: m.text == get_text(m.from_user.id, "calculator"))
async def start_calc(msg: types.Message):
    uid = msg.from_user.id
    if uid not in user_lang:
        await msg.answer("Сначала выберите язык.")
        return
    models_list = [model["name"] for cat in MODELS.values() for model in cat]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for model in models_list:
        kb.add(KeyboardButton(model))
    kb.add(KeyboardButton(get_text(uid, "back")))

    await msg.answer(get_text(uid, "choose_model"), reply_markup=kb)
    await CalcForm.model.set()


@dp.message_handler(state=CalcForm.model)
async def calc_hours(msg: types.Message, state: FSMContext):
    await state.update_data(model=msg.text)
    await msg.answer("⌚ Сколько часов в день работает техника?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.hours_per_day)
async def calc_days(msg: types.Message, state: FSMContext):
    await state.update_data(hours_per_day=int(msg.text))
    await msg.answer("📅 Сколько дней в месяц техника используется?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.days_per_month)
async def calc_months(msg: types.Message, state: FSMContext):
    await state.update_data(days_per_month=int(msg.text))
    await msg.answer("📆 На сколько месяцев рассчитывается использование?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.months_total)
async def calc_rent(msg: types.Message, state: FSMContext):
    await state.update_data(months_total=int(msg.text))
    await msg.answer("💸 Сколько стоит аренда техники в месяц?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.rent_per_month)
async def calc_salary(msg: types.Message, state: FSMContext):
    await state.update_data(rent_per_month=int(msg.text))
    await msg.answer("👷 Зарплата оператора в месяц?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.operator_salary)
async def calc_fuel_per_day(msg: types.Message, state: FSMContext):
    await state.update_data(operator_salary=int(msg.text))
    await msg.answer("⛽ Сколько литров топлива расходуется в день?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.fuel_per_day)
async def calc_fuel_price(msg: types.Message, state: FSMContext):
    await state.update_data(fuel_per_day=int(msg.text))
    await msg.answer("💰 Цена за литр топлива?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.fuel_price)
async def calc_service(msg: types.Message, state: FSMContext):
    await state.update_data(fuel_price=int(msg.text))
    await msg.answer("🔧 Расходы на обслуживание за всё время?")
    await CalcForm.next()


@dp.message_handler(state=CalcForm.service_cost)
async def finish_calc(msg: types.Message, state: FSMContext):
    await state.update_data(service_cost=int(msg.text))
    data = await state.get_data()

    model_name = data["model"]
    model = None
    for cat_items in MODELS.values():
        for item in cat_items:
            if item["name"] == model_name:
                model = item
                break
        if model:
            break

    if not model:
        await msg.answer("❌ Модель не найдена.", reply_markup=get_menu(msg.from_user.id))
        await state.finish()
        return

    # Расчёт
    hours_per_day = data["hours_per_day"]
    days_per_month = data["days_per_month"]
    months_total = data["months_total"]
    rent_per_month = data["rent_per_month"]
    operator_salary = data["operator_salary"]
    fuel_per_day = data["fuel_per_day"]
    fuel_price = data["fuel_price"]
    service_cost = data["service_cost"]

    fuel_total = fuel_per_day * fuel_price * days_per_month * months_total
    own_cost = operator_salary * months_total + fuel_total + service_cost
    rent_total = rent_per_month * months_total
    saving = rent_total - own_cost

    try:
        price = int(model["price"].replace(" ", ""))
    except:
        price = 0

    if saving <= 0:
        await msg.answer(
            f"❗ По введённым данным техника не даёт выгоды.\n"
            f"Вы тратите {own_cost:,} сум, а аренда стоит {rent_total:,} сум.",
            reply_markup=get_menu(msg.from_user.id)
        )
    else:
        payback = round(price / (saving / months_total), 1) if price else 0
        text = (
            f"✅ Вы экономите ~{saving:,} сум за {months_total} мес.\n"
            f"📉 Срок окупаемости: {payback} мес."
        )
        await msg.answer(text, reply_markup=get_menu(msg.from_user.id))

    await state.finish()
   

# ========== СРАВНЕНИЕ МОДЕЛЕЙ ==========
compare_state = {}

@dp.message_handler(lambda m: m.text.startswith("🆚"))
async def start_compare(msg: types.Message):
    uid = msg.from_user.id
    compare_state[uid] = {"step": 1, "selected": []}
    buttons = []
    for cat, items in MODELS.items():
        for item in items:
            buttons.append(item["name"])
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for name in buttons:
        kb.add(KeyboardButton(name))
    await msg.answer("Выберите первую модель для сравнения:", reply_markup=kb)

@dp.message_handler(lambda m: m.text in [item["name"] for items in MODELS.values() for item in items])
async def handle_compare_choice(msg: types.Message):
    uid = msg.from_user.id
    if uid not in compare_state:
        return
    compare_state[uid]["selected"].append(msg.text)
    if compare_state[uid]["step"] == 1:
        compare_state[uid]["step"] = 2
        await msg.answer("Теперь выберите вторую модель:")
    elif compare_state[uid]["step"] == 2:
        model1 = model2 = None
        for items in MODELS.values():
            for item in items:
                if item["name"] == compare_state[uid]["selected"][0]:
                    model1 = item
                if item["name"] == compare_state[uid]["selected"][1]:
                    model2 = item
        if not model1 or not model2:
            await msg.answer("❌ Не удалось найти одну из моделей.")
            return
        text = f"🆚 Сравнение:\n\n{model1['name']} VS {model2['name']}\n"
        text += "----------------------------------\n"
        specs = set(model1.get("specs", {}).keys()) & set(model2.get("specs", {}).keys())
        for spec in specs:
            val1 = model1['specs'][spec]
            val2 = model2['specs'][spec]
            text += f"{spec}: {val1} | {val2}\n"
        await msg.answer(text, reply_markup=get_menu(uid))
        del compare_state[uid]

@dp.message_handler()
async def unknown(msg: types.Message):
    await msg.answer(get_text(msg.from_user.id, "unknown"), reply_markup=get_menu(msg.from_user.id))

if __name__ == "__main__":
    print("✅ Бот запущен")
    from aiogram import executor
    loop = asyncio.get_event_loop()
    loop.run_until_complete(drop_pending_updates(bot))
    executor.start_polling(dp, skip_updates=True)




 
