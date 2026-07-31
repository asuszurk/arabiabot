import asyncio
from fastapi import FastAPI
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# === НАСТРОЙКИ БОТА ===
TOKEN = '8811014865:AAHHpNRmFkvmtlT8i2Kx188BHz2kGWW39VI'
bot = Bot(token=TOKEN)
dp = Dispatcher()
WEB_APP_URL = "https://arabiabot-production.up.railway.app"

# === НАСТРОЙКИ FASTAPI ===
app = FastAPI()
DB_NAME = "learning_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, score INTEGER DEFAULT 0, level INTEGER DEFAULT 1)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY, 
            expires_at TEXT, 
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

# Эндпоинт проверки подписки для Web App
@app.get("/api/check-subscription/{user_id}")
async def check_subscription(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expires_at, status FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        expires_at = datetime.now() + timedelta(days=3)
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO subscriptions (user_id, expires_at, status) VALUES (?, ?, 'trial')", (user_id, expires_str))
        conn.commit()
        conn.close()
        return {"active": True, "expires_at": expires_str, "is_trial": True}

    expires_at_str, status = row
    expires_at = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
    conn.close()
    
    if expires_at > datetime.now():
        return {"active": True, "expires_at": expires_at_str, "is_trial": (status == 'trial')}
    else:
        return {"active": False, "message": "Subscription expired"}

# Обработчик команды /start в боте
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть приложение", 
                    web_app=WebAppInfo(url=WEB_APP_URL)
                )
            ]
        ]
    )
    await message.answer(
        "Ассаляму алейкум! Добро пожаловать в бот по изучению арабского языка и таджвида.\n\n"
        "Нажмите кнопку ниже, чтобы открыть приложение:",
        reply_markup=keyboard
    )

# Фоновый запуск бота при старте сервера
@app.on_event("startup")
async def on_startup():
    init_db()
    # Установка кнопки меню в профиле
    try:
        await bot.set_chat_menu_button(
            menu_button=types.MenuButtonWebApp(
                text="Открыть приложение",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        )
    except Exception as e:
        print(f"Menu button error: {e}")
    
    # Запуск поллинга бота в фоновой задаче
    asyncio.create_task(dp.start_polling(bot))