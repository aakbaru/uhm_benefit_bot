
# -*- coding: utf-8 -*-
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import logging
import json

import os
API_TOKEN = os.getenv("BOT_TOKEN")

user_lang = {}

with open("texts_ru.json", encoding="utf-8") as f:
    texts_ru = json.load(f)

with open("texts_uz.json", encoding="utf-8") as f:
    texts_uz = json.load(f)

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
    hours = State()
    days = State()
    months = State()
    rent = State()
    salary = State()
    fuel = State()
    fuel_price = State()
    service = State()

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    lang_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    lang_kb.add("🇷🇺 Русский", "🇺🇿 O‘zbekcha")
    await msg.answer("🇷🇺 Выберите язык / 🇺🇿 Tilni tanlang", reply_markup=lang_kb)

@dp.message_handler(lambda m: m.text in ["🇷🇺 Русский", "🇺🇿 O‘zbekcha"])
async def set_lang(msg: types.Message):
    user_lang[msg.from_user.id] = "ru" if "Рус" in msg.text else "uz"
    await msg.answer(get_text(msg.from_user.id, "start"), reply_markup=get_menu(msg.from_user.id))

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
    if not MODELS:
        await msg.answer(get_text(uid, "empty_catalog"))
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



@dp.message_handler(lambda m: m.text.startswith("📊"))
async def start_calc(msg: types.Message):
    text = "Выберите модель техники:"
    buttons = []
    for cat, items in MODELS.items():
        for item in items:
            buttons.append(item["name"])
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for btn in buttons:
        markup.add(KeyboardButton(btn))
    await msg.answer(text, reply_markup=markup)
    await CalcForm.model.set()

@dp.message_handler(state=CalcForm.model)
async def calc_model(msg: types.Message, state: FSMContext):
    selected = msg.text
    for items in MODELS.values():
        for item in items:
            if item["name"] == selected:
                await state.update_data(model=item)
                await msg.answer("Сколько часов в день используется техника?")
                await CalcForm.next()
                return
    await msg.answer("Модель не найдена, выберите из списка.")

@dp.message_handler(state=CalcForm.hours)
async def calc_hours(msg: types.Message, state: FSMContext):
    await state.update_data(hours=int(msg.text))
    await msg.answer("Сколько дней в месяц работает техника?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.days)
async def calc_days(msg: types.Message, state: FSMContext):
    await state.update_data(days=int(msg.text))
    await msg.answer("Сколько месяцев планируете владеть техникой?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.months)
async def calc_months(msg: types.Message, state: FSMContext):
    await state.update_data(months=int(msg.text))
    await msg.answer("Сколько вы платите за аренду техники в месяц?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.rent)
async def calc_rent(msg: types.Message, state: FSMContext):
    await state.update_data(rent=int(msg.text))
    await msg.answer("Какая будет зарплата оператора?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.salary)
async def calc_salary(msg: types.Message, state: FSMContext):
    await state.update_data(salary=int(msg.text))
    await msg.answer("Сколько литров топлива расходуется в день?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.fuel)
async def calc_fuel(msg: types.Message, state: FSMContext):
    await state.update_data(fuel=float(msg.text))
    await msg.answer("Сколько стоит 1 литр топлива?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.fuel_price)
async def calc_fuel_price(msg: types.Message, state: FSMContext):
    await state.update_data(fuel_price=float(msg.text))
    await msg.answer("Сколько в месяц стоит обслуживание?")
    await CalcForm.next()

@dp.message_handler(state=CalcForm.service)
async def calc_service(msg: types.Message, state: FSMContext):
    await state.update_data(service=int(msg.text))
    data = await state.get_data()
    model = data["model"]
    machine_price = int(model["price"].replace(" ", ""))
    fuel_total = data['fuel'] * data['days'] * data['fuel_price']
    own_cost = data['salary'] + fuel_total + data['service']
    saving = data['rent'] - own_cost

    if saving <= 0:
        await msg.answer(
            f"❗ По введённым данным техника не даёт выгоды.\n"
            f"Вы тратите {int(own_cost):,} сум/мес, а аренда стоит {int(data['rent']):,} сум.\n"
            f"Попробуйте изменить параметры, чтобы увидеть реальную выгоду.",
            reply_markup=get_menu(msg.from_user.id)
        )
    else:
        payback = round(machine_price / saving, 1)
        response = (
            f"✅ Вы экономите ~{int(saving):,} сум в месяц\n"
            f"📉 Срок окупаемости {model['name']}: {payback} мес."
        )

        if payback > 24:
            # Ищем другую модель из той же категории с меньшей ценой
            suggestion = None
            for cat, items in MODELS.items():
                if model in items:
                    cheaper = [m for m in items if int(m["price"].replace(" ", "")) < machine_price and m != model]
                    if cheaper:
                        suggestion = min(cheaper, key=lambda m: int(m["price"].replace(" ", "")))
                    break

            if suggestion:
                response += f"\n\n💡 Попробуйте {suggestion['name']} — дешевле на {machine_price - int(suggestion['price'].replace(' ', '')):,} сум."

        await msg.answer(response, reply_markup=get_menu(msg.from_user.id))

    await state.finish()

    await state.update_data(service=int(msg.text))
    data = await state.get_data()
    model = data["model"]
    machine_price = int(model["price"].replace(" ", ""))
    fuel_total = data['fuel'] * data['days'] * data['fuel_price']
    own_cost = data['salary'] + fuel_total + data['service']
    saving = data['rent'] - own_cost

    if saving <= 0:
        await msg.answer(
            f"❗ По введённым данным техника не даёт выгоды.\n"
            f"Вы тратите {int(own_cost):,} сум/мес, а аренда стоит {int(data['rent']):,} сум.\n"
            f"Попробуйте изменить параметры, чтобы увидеть реальную выгоду.",
            reply_markup=get_menu(msg.from_user.id)
        )
    else:
        payback = round(machine_price / saving, 1)
        await msg.answer(
            f"✅ Вы экономите ~{int(saving):,} сум в месяц\n"
            f"📉 Срок окупаемости {model['name']}: {payback} мес.",
            reply_markup=get_menu(msg.from_user.id)
        )
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
from aiohttp import web

async def on_startup(app):
    await bot.set_webhook("https://uhm-bot.onrender.com/webhook")  # ЗАМЕНИ НА СВОЙ URL

async def on_shutdown(app):
    await bot.delete_webhook()

def start():
    from aiogram import web

    app = web.Application()
    app.router.add_post("/webhook", dp.router)  # Webhook endpoint
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    start()

 
