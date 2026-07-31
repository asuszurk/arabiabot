import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import sqlite3
from datetime import datetime, timedelta

app = FastAPI()
DB_NAME = "learning_bot.db"

# Создаем таблицы в базе данных при старте сервера, если их нет
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY, 
            expires_at TEXT, 
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Главная страница веб-приложения (отдает твой index.html)
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Index.html not found</h1>"

# Эндпоинт проверки подписки для студентов
@app.get("/api/check-subscription/{user_id}")
async def check_subscription(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expires_at, status FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        # Автоматический триал 3 дня для новых учеников
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