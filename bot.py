import asyncio
from io import BytesIO
from gtts import gTTS
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from PIL import Image, ImageDraw, ImageFont
import sqlite3

# Токен твоего бота
TOKEN = '8811014865:AAHHpNRmFkvmtlT8i2Kx188BHz2kGWW39VI'

# Твой уникальный Telegram ID для доступа к админке
ADMIN_ID = 7942465558  

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ссылка на ваше веб-приложение (замените при смене туннеля Cloudflare, если нужно)
WEB_APP_URL = "https://arabiabot-production.up.railway.app"

# База данных алфавита
ALPHABET = {
    "أ": "Алиф", "ب": "Ба", "ت": "Та", "ث": "Са", "ج": "Джим", 
    "ح": "Ха", "خ": "Ха (горловое)", "د": "Даль", "ذ": "Заль", "ر": "Ра", 
    "ز": "Зай", "س": "Син", "ش": "Шин", "ص": "Сад", "ض": "Дад", 
    "ط": "Та (твердая)", "ظ": "За (твердая)", "ع": "Айн", "غ": "Гайн", "ف": "Фа", 
    "ق": "Каф", "ك": "Кяф", "ل": "Лям", "م": "Мим", "ن": "Нун", 
    "هـ": "Ха (мягкая)", "و": "Вав", "ي": "Йа", "ء": "Хамза (гортанная смычка)"
}

DICTIONARY_CATEGORIES = {
    "basic": {
        "title": "📜 Базовые слова",
        "items": {"نَعَم": "Да", "لَا": "Нет", "شُكْرًا": "Спасибо", "مِنْ فَضْلِكَ": "Пожалуйста"}
    },
    "phrases": {
        "title": "💬 Разговорные фразы",
        "items": {
            "مَرْحَبًا": "Привет", "كَيْفَ حَالُكَ؟": "Как дела?", "إِسْمِي إِبْرَاهِيم": "Меня зовут Ибрагим",
            "أَهْلًا وَسَهْلًا": "Добро пожаловать", "إِلَى اللِّقَاءِ": "До свидания", "صَبَاحُ الْخَيْرِ": "Доброе утро"
        }
    },
    "study": {
        "title": "🎒 Учёба",
        "items": {"كِتَاب": "Книга", "قَلَم": "Ручка", "مَدْرَسَة": "Школа", "دَفْتَر": "Тетрадь", "أُسْتَاذ": "Учитель"}
    },
    "food": {
        "title": "🍎 Еда и Вода",
        "items": {"مَاء": "Вода", "خُبْز": "Хлеб", "طَعَام": "Еда", "حَلِيب": "Молоко", "تُفَّاح": "Яблоко"}
    }
}

WORDS = {}
for cat in ["basic", "study", "food"]:
    WORDS.update(DICTIONARY_CATEGORIES[cat]["items"])
PHRASES = DICTIONARY_CATEGORIES["phrases"]["items"]

# === СТРУКТУРА ТАДЖВИДА ===
GRAMMAR_SECTIONS = {
    "taj_nm": {
        "title": "✨ Правила Нун и Мим",
        "parent": "tajweed",
        "lessons": [
            {
                "id": "tnm1", "name": "Нун с сукуном и танвин",
                "rule": "🔹 **Нун с сукуном (نْ) и танвин (ً ٍ ٌ)**\n\n1. **Изхар (إظهار)** — читать ясно, без изменений перед буквами: `ء هـ ع ح غ خ`.\n2. **Идгам (إдогам)** — слияние. С гунной (2 хараката) перед `ي ن м و`. Без гунны перед `ل ر`.\n*Исключение:* Если они в одном слове (الدنيا, بنيان, قنوان, صنوان), идгам не применяется.\n3. **Икляب (إقلاب)** — перед `ب` звук `ن` заменяется на скрытый `م` с гунной.\n4. **Ихфа (إخفاء)** — перед остальными 15 буквами нун читается скрыто с гунной."
            },
            {
                "id": "tnm2", "name": "Мим с сукуном и Гунна",
                "rule": "🔹 **Мим с сукуном (مْ) и Гунна**\n\n**Правила Мим с сукуном:**\n1. *Ихфа шафави* — перед `ب`.\n2. *Идгам шафави* — перед `م`.\n3. *Изхар шафави* — перед всеми остальными буквами.\n\n**Гунна (غنة):**\nНосовое звучание длительностью 2 хараката. Обязательно при удвоенных `نّ` и `مّ`, а также при идгаме с гунной, ихфа и иклябе."
            }
        ]
    }
}

# === РАБОТА С СУБД SQLITE ===
def init_db():
    conn = sqlite3.connect("learning_bot.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, score INTEGER DEFAULT 0, level INTEGER DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS custom_images (item_key TEXT PRIMARY KEY, file_id TEXT)")
    conn.commit()
    conn.close()

def get_user(user_id, username):
    conn = sqlite3.connect("learning_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT score, level FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute("INSERT INTO users (user_id, username, score, level) VALUES (?, ?, 0, 1)", (user_id, username))
        conn.commit()
        score, level = 0, 1
    else:
        score, level = row[0], row[1]
    conn.close()
    return {"score": score, "level": level}

# === ХЕНДЛЕРЫ БОТА ===
from aiogram import types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

@app.message(commands=["start"])
async def cmd_start(message: types.Message):
    # Создаем клавиатуру с единственной рабочей кнопкой открытия Web App
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть приложение", 
                    web_app=WebAppInfo(url="https://arabiabot-production.up.railway.app")
                )
            ]
        ]
    )
    
    await message.answer(
        "Ассаляму алейкум! Добро пожаловать в бот по изучению арабского языка и таджвида.\n\n"
        "Нажмите кнопку ниже, чтобы открыть приложение:",
        reply_markup=keyboard
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Панель администратора активна.")

async def main():
    init_db()
    print("Бот успешно запущен (без лишних кнопок в чате)!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())