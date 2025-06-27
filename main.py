
# -*- coding: utf-8 -*-
import os
import json
import logging
from typing import Dict, List, Any, Optional, Set

from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import TelegramAPIError
from dotenv import load_dotenv
load_dotenv()

# ==================== КОНФИГУРАЦИЯ И НАСТРОЙКИ ====================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ADMIN_IDS = set(map(int, os.getenv("ADMIN_IDS", "").split(','))) if os.getenv("@UHMLT") else set()
    CONTACT_MANAGER = os.getenv("CONTACT_MANAGER", "@UHMLT")
    CONTACT_PHONE = os.getenv("CONTACT_PHONE", "+998 90 977 31 35")
    POLICY_URL = os.getenv("POLICY_URL", "https://uhmlandtech.uz/uhm/")
    SOCIAL_MEDIA = {
        'instagram': os.getenv("INSTAGRAM_URL", "https://www.instagram.com/uhm.uz/"),
        'facebook': os.getenv("FACEBOOK_URL", "https://www.facebook.com/uhmtashkent"),
        'telegram': os.getenv("TELEGRAM_URL", "https://t.me/uhmuz")
    }

# Проверка обязательных конфигураций
if not Config.BOT_TOKEN:
    raise ValueError("Токен бота не указан в переменных окружения (BOT_TOKEN)")

# ==================== МОДЕЛИ ДАННЫХ И КОНСТАНТЫ ====================

class UserData:
    """Класс для хранения данных пользователя"""
    def __init__(self):
        self.language: str = 'ru'
        self.compare_selection: List[str] = []
        self.calculator_data: Dict[str, Any] = {}

# Глобальное хранилище данных пользователей (в продакшене следует заменить на БД)
user_data: Dict[int, UserData] = {}

# Конфигурация обязательных ключей в JSON-файлах
REQUIRED_KEYS = {
    'texts_ru.json': ['start', 'menu', 'unknown', 'back', 'choose_category', 
                     'choose_model', 'calculator', 'catalog', 'compare'],
    'texts_uz.json': ['start', 'menu', 'unknown', 'back', 'choose_category',
                     'choose_model', 'calculator', 'catalog', 'compare']
}

# ==================== УТИЛИТЫ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def load_json_data() -> Dict[str, Any]:
    """Загружает и валидирует данные из JSON файлов"""
    try:
        with open("texts_ru.json", encoding="utf-8") as f:
            texts_ru = json.load(f)
        with open("texts_uz.json", encoding="utf-8") as f:
            texts_uz = json.load(f)
        with open("models.json", encoding="utf-8") as f:
            models = json.load(f)

        # Валидация данных
        for filename, required_keys in REQUIRED_KEYS.items():
            data = texts_ru if 'ru' in filename else texts_uz if 'uz' in filename else models
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Обязательный ключ '{key}' отсутствует в {filename}")

        return {
            "TEXTS": {'ru': texts_ru, 'uz': texts_uz},
            "MODELS": models
        }
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        raise

# Загрузка данных
try:
    data = load_json_data()
    TEXTS = data["TEXTS"]
    MODELS = data["MODELS"]
except Exception as e:
    logger.critical(f"Критическая ошибка загрузки данных: {e}")
    exit(1)

def get_user(uid: int) -> UserData:
    """Возвращает или создает данные пользователя"""
    if uid not in user_data:
        user_data[uid] = UserData()
    return user_data[uid]

def get_text(uid: int, key: str, **kwargs) -> str:
    """Возвращает локализованный текст с подстановкой переменных"""
    user = get_user(uid)
    text = TEXTS.get(user.language, {}).get(key, TEXTS['ru'].get(key, "❌ Текст не найден"))
    return text.format(**kwargs) if kwargs else text

def create_menu(uid: int) -> ReplyKeyboardMarkup:
    """Создает клавиатуру меню"""
    menu_items = TEXTS[get_user(uid).language]['menu']
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(*[KeyboardButton(item) for item in menu_items])
    return kb

def create_models_keyboard(uid: int) -> ReplyKeyboardMarkup:
    """Создает клавиатуру с моделями техники"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    models_list = [model["name"] for category in MODELS.values() for model in category]
    kb.add(*[KeyboardButton(model) for model in models_list])
    kb.add(KeyboardButton(get_text(uid, "back")))
    return kb

def create_categories_keyboard(uid: int) -> ReplyKeyboardMarkup:
    """Создает клавиатуру с категориями техники"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(*[KeyboardButton(category) for category in MODELS.keys()])
    kb.add(KeyboardButton(get_text(uid, "back")))
    return kb

async def delete_previous_messages(bot: Bot, chat_id: int, message_ids: List[int]):
    """Удаляет предыдущие сообщения бота"""
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except TelegramAPIError:
            pass

# ==================== СОСТОЯНИЯ FSM ====================

class CalculatorStates(StatesGroup):
    """Состояния для калькулятора экономии"""
    model = State()
    hours_per_day = State()
    days_per_month = State()
    months_total = State()
    rent_per_month = State()
    operator_salary = State()
    fuel_per_day = State()
    fuel_price = State()
    service_cost = State()

# ==================== ИНИЦИАЛИЗАЦИЯ БОТА ====================

bot = Bot(token=Config.BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

@dp.message_handler(commands=["start", "help", "language"])
async def start_handler(message: types.Message, state: FSMContext):
    """Обработчик стартовых команд"""
    await state.finish()
    user = get_user(message.from_user.id)
    
    if message.get_command() == "language":
        await prompt_language(message)
        return
    
    welcome_text = (
        "👋 Добро пожаловать в бота для сравнения строительной техники!\n\n"
        "🇷🇺 Выберите язык / 🇺🇿 Tilni tanlang"
    )
    
    await message.answer(welcome_text, reply_markup=create_language_keyboard())

async def prompt_language(message: types.Message):
    """Запрашивает выбор языка"""
    await message.answer(
        "🌍 Выберите язык / Tilni tanlang:",
        reply_markup=create_language_keyboard()
    )

def create_language_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру выбора языка"""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🇷🇺 Русский", "🇺🇿 O‘zbekcha")
    return kb

@dp.message_handler(lambda m: m.text in ["🇷🇺 Русский", "🇺🇿 O‘zbekcha"])
async def set_language_handler(message: types.Message):
    """Устанавливает язык пользователя"""
    user = get_user(message.from_user.id)
    user.language = "ru" if "Рус" in message.text else "uz"
    
    await message.answer(
        get_text(message.from_user.id, "start"),
        reply_markup=create_menu(message.from_user.id)
    )

# ==================== ОБРАБОТЧИКИ МЕНЮ ====================

@dp.message_handler(lambda m: m.text == get_text(m.from_user.id, "catalog"))
async def catalog_handler(message: types.Message):
    """Обработчик каталога техники"""
    await message.answer(
        get_text(message.from_user.id, "choose_category"),
        reply_markup=create_categories_keyboard(message.from_user.id)
    )

@dp.message_handler(lambda m: m.text in MODELS.keys())
async def category_handler(message: types.Message):
    """Обработчик выбора категории техники"""
    category = message.text
    models = MODELS[category]
    
    for model in models:
        caption = f"<b>{model['name']}</b> — {model['price']} сум\n"
        if "specs" in model:
            for spec, value in model["specs"].items():
                caption += f"\n• <i>{spec}:</i> {value}"
        
        try:
            await message.answer_photo(
                model["image"],
                caption=caption,
                reply_markup=create_menu(message.from_user.id)
            )
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            await message.answer(caption)

@dp.message_handler(lambda m: m.text == get_text(m.from_user.id, "calculator"))
async def calculator_handler(message: types.Message):
    """Обработчик запуска калькулятора"""
    await message.answer(
        get_text(message.from_user.id, "choose_model"),
        reply_markup=create_models_keyboard(message.from_user.id)
    )
    await CalculatorStates.model.set()

# ==================== ОБРАБОТЧИКИ КАЛЬКУЛЯТОРА ====================

@dp.message_handler(state=CalculatorStates.model)
async def process_model(message: types.Message, state: FSMContext):
    """Обработчик выбора модели для калькулятора"""
    model_name = message.text
    model_exists = any(model_name in (m["name"] for m in models) for models in MODELS.values())
    
    if not model_exists:
        await message.answer("❌ Модель не найдена. Пожалуйста, выберите из списка.")
        return
    
    await state.update_data(model=model_name)
    await message.answer("⌚ Сколько часов в день работает техника?")
    await CalculatorStates.hours_per_day.set()

async def validate_number_input(message: types.Message, min_val: float = 0, max_val: float = float('inf')) -> Optional[float]:
    """Валидирует числовой ввод"""
    try:
        value = float(message.text)
        if value <= min_val or value > max_val:
            raise ValueError
        return value
    except ValueError:
        await message.answer(f"Пожалуйста, введите число от {min_val} до {max_val}")
        return None

@dp.message_handler(state=CalculatorStates.hours_per_day)
async def process_hours(message: types.Message, state: FSMContext):
    """Обработчик часов работы"""
    hours = await validate_number_input(message, min_val=0, max_val=24)
    if hours is None:
        return
    
    await state.update_data(hours_per_day=hours)
    await message.answer("📅 Сколько дней в месяц техника используется?")
    await CalculatorStates.days_per_month.set()

@dp.message_handler(state=CalculatorStates.days_per_month)
async def process_days(message: types.Message, state: FSMContext):
    """Обработчик дней использования"""
    days = await validate_number_input(message, min_val=0, max_val=31)
    if days is None:
        return
    
    await state.update_data(days_per_month=days)
    await message.answer("📆 На сколько месяцев рассчитывается использование?")
    await CalculatorStates.months_total.set()

@dp.message_handler(state=CalculatorStates.months_total)
async def process_months(message: types.Message, state: FSMContext):
    """Обработчик месяцев использования"""
    months = await validate_number_input(message, min_val=1)
    if months is None:
        return
    
    await state.update_data(months_total=months)
    await message.answer("💸 Сколько стоит аренда техники в месяц?")
    await CalculatorStates.rent_per_month.set()

@dp.message_handler(state=CalculatorStates.rent_per_month)
async def process_rent(message: types.Message, state: FSMContext):
    """Обработчик стоимости аренды"""
    rent = await validate_number_input(message, min_val=1)
    if rent is None:
        return
    
    await state.update_data(rent_per_month=rent)
    await message.answer("👷 Зарплата оператора в месяц?")
    await CalculatorStates.operator_salary.set()

@dp.message_handler(state=CalculatorStates.operator_salary)
async def process_salary(message: types.Message, state: FSMContext):
    """Обработчик зарплаты оператора"""
    salary = await validate_number_input(message, min_val=1)
    if salary is None:
        return
    
    await state.update_data(operator_salary=salary)
    await message.answer("⛽ Сколько литров топлива расходуется в день?")
    await CalculatorStates.fuel_per_day.set()

@dp.message_handler(state=CalculatorStates.fuel_per_day)
async def process_fuel_consumption(message: types.Message, state: FSMContext):
    """Обработчик расхода топлива"""
    fuel = await validate_number_input(message, min_val=0)
    if fuel is None:
        return
    
    await state.update_data(fuel_per_day=fuel)
    await message.answer("💰 Цена за литр топлива?")
    await CalculatorStates.fuel_price.set()

@dp.message_handler(state=CalculatorStates.fuel_price)
async def process_fuel_price(message: types.Message, state: FSMContext):
    """Обработчик цены топлива"""
    price = await validate_number_input(message, min_val=0)
    if price is None:
        return
    
    await state.update_data(fuel_price=price)
    await message.answer("🔧 Расходы на обслуживание за всё время?")
    await CalculatorStates.service_cost.set()

@dp.message_handler(state=CalculatorStates.service_cost)
async def process_service_cost(message: types.Message, state: FSMContext):
    """Завершение расчета и вывод результатов"""
    service_cost = await validate_number_input(message, min_val=0)
    if service_cost is None:
        return
    
    await state.update_data(service_cost=service_cost)
    data = await state.get_data()
    user = get_user(message.from_user.id)
    
    # Находим модель в каталоге
    model = next(
        (item for items in MODELS.values() for item in items if item["name"] == data["model"]),
        None
    )
    
    if not model:
        await message.answer("❌ Модель не найдена.", reply_markup=create_menu(message.from_user.id))
        await state.finish()
        return
    
    # Расчет экономии
    hours = data["hours_per_day"]
    days = data["days_per_month"]
    months = data["months_total"]
    rent = data["rent_per_month"]
    salary = data["operator_salary"]
    fuel_cons = data["fuel_per_day"]
    fuel_price = data["fuel_price"]
    service = data["service_cost"]
    
    fuel_total = fuel_cons * fuel_price * days * months
    own_cost = salary * months + fuel_total + service
    rent_total = rent * months
    saving = rent_total - own_cost
    
    try:
        price = int(model["price"].replace(" ", "").replace("сум", ""))
    except:
        price = 0
    
    if saving <= 0:
        result_text = (
            f"❗ По введённым данным техника не даёт выгоды.\n"
            f"Вы тратите {own_cost:,} сум, а аренда стоит {rent_total:,} сум."
        )
    else:
        payback = round(price / (saving / months), 1) if price else 0
        result_text = (
            f"✅ Вы экономите ~{saving:,} сум за {months} мес.\n"
            f"📉 Срок окупаемости: {payback} мес.\n\n"
            f"🔹 Собственные расходы: {own_cost:,} сум\n"
            f"🔹 Стоимость аренды: {rent_total:,} сум"
        )
    
    await message.answer(result_text, reply_markup=create_menu(message.from_user.id))
    await state.finish()

# ==================== ОБРАБОТЧИКИ СРАВНЕНИЯ МОДЕЛЕЙ ====================

@dp.message_handler(lambda m: m.text == get_text(m.from_user.id, "compare"))
async def start_compare_handler(message: types.Message):
    """Начало сравнения моделей"""
    user = get_user(message.from_user.id)
    user.compare_selection = []
    
    await message.answer(
        "Выберите первую модель для сравнения:",
        reply_markup=create_models_keyboard(message.from_user.id)
    )

@dp.message_handler(lambda m: m.text in [model["name"] for models in MODELS.values() for model in models])
async def compare_model_handler(message: types.Message):
    """Обработчик выбора моделей для сравнения"""
    user = get_user(message.from_user.id)
    model_name = message.text
    
    if model_name in user.compare_selection:
        await message.answer("Эта модель уже выбрана для сравнения.")
        return
    
    user.compare_selection.append(model_name)
    
    if len(user.compare_selection) == 1:
        await message.answer(
            "Теперь выберите вторую модель:",
            reply_markup=create_models_keyboard(message.from_user.id)
        )
    elif len(user.compare_selection) == 2:
        model1 = next(
            (item for items in MODELS.values() for item in items if item["name"] == user.compare_selection[0]),
            None
        )
        model2 = next(
            (item for items in MODELS.values() for item in items if item["name"] == user.compare_selection[1]),
            None
        )
        
        if not model1 or not model2:
            await message.answer("❌ Не удалось найти одну из моделей.")
            user.compare_selection = []
            return
        
        comparison_text = generate_comparison_text(model1, model2)
        await message.answer(comparison_text, reply_markup=create_menu(message.from_user.id))
        user.compare_selection = []

def generate_comparison_text(model1: Dict, model2: Dict) -> str:
    """Генерирует текст для сравнения моделей"""
    text = (
        f"🆚 <b>Сравнение моделей</b>\n\n"
        f"<u>{model1['name']}</u> vs <u>{model2['name']}</u>\n\n"
    )
    
    # Общие характеристики
    common_specs = set(model1.get("specs", {}).keys()) & set(model2.get("specs", {}).keys())
    if common_specs:
        text += "📊 <b>Общие характеристики:</b>\n"
        for spec in common_specs:
            val1 = model1['specs'][spec]
            val2 = model2['specs'][spec]
            text += f"• {spec}: {val1} | {val2}\n"
        text += "\n"
    
    # Уникальные характеристики первой модели
    unique1 = set(model1.get("specs", {}).keys()) - set(model2.get("specs", {}).keys())
    if unique1:
        text += f"🔹 <b>Уникальные характеристики {model1['name']}:</b>\n"
        for spec in unique1:
            text += f"• {spec}: {model1['specs'][spec]}\n"
        text += "\n"
    
    # Уникальные характеристики второй модели
    unique2 = set(model2.get("specs", {}).keys()) - set(model1.get("specs", {}).keys())
    if unique2:
        text += f"🔸 <b>Уникальные характеристики {model2['name']}:</b>\n"
        for spec in unique2:
            text += f"• {spec}: {model2['specs'][spec]}\n"
    
    # Цены
    text += f"\n💵 <b>Цены:</b>\n"
    text += f"• {model1['name']}: {model1['price']}\n"
    text += f"• {model2['name']}: {model2['price']}\n"
    
    return text

# ==================== ОБРАБОТЧИКИ КОНТАКТОВ И ИНФОРМАЦИИ ====================

@dp.message_handler(lambda m: m.text.startswith("📞"))
async def contact_handler(message: types.Message):
    """Обработчик контактов"""
    contact_text = (
        f"📞 <b>Контактная информация:</b>\n\n"
        f"👨‍💼 Менеджер: {Config.CONTACT_MANAGER}\n"
        f"📱 Телефон: {Config.CONTACT_PHONE}"
    )
    await message.answer(contact_text)

@dp.message_handler(lambda m: m.text.startswith("🔒"))
async def policy_handler(message: types.Message):
    """Обработчик политики конфиденциальности"""
    policy_text = (
        f"🔐 <b>Политика конфиденциальности:</b>\n\n"
        f"📄 Документ: {Config.POLICY_URL}\n\n"
        f"<b>Мы в соцсетях:</b>\n"
        f"📸 Instagram: {Config.SOCIAL_MEDIA['instagram']}\n"
        f"📘 Facebook: {Config.SOCIAL_MEDIA['facebook']}\n"
        f"📢 Telegram: {Config.SOCIAL_MEDIA['telegram']}"
    )
    await message.answer(policy_text)

# ==================== ОБРАБОТЧИК ОШИБОК ====================

@dp.errors_handler()
async def error_handler(update: types.Update, exception: Exception):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка при обработке запроса: {exception}", exc_info=True)
    
    if isinstance(update, types.Message):
        chat_id = update.chat.id
        try:
            await update.answer("⚠ Произошла ошибка. Пожалуйста, попробуйте позже.")
        except TelegramAPIError:
            pass
    
    return True

# ==================== ЗАПУСК БОТА ====================

async def on_startup(dp: Dispatcher):
    """Действия при запуске бота"""
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот успешно запущен")
    
    # Уведомление админов
    for admin_id in Config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🟢 Бот успешно запущен")
        except TelegramAPIError:
            pass

async def on_shutdown(dp: Dispatcher):
    """Действия при выключении бота"""
    logger.info("Выключение бота...")
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
    logger.info("Бот успешно выключен")

if __name__ == "__main__":
    try:
        executor.start_polling(
            dp,
            skip_updates=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown
        )
    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {e}", exc_info=True)
        exit(1)
