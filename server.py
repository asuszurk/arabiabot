import os
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
from datetime import datetime, timedelta

app = FastAPI()
DB_NAME = "learning_bot.db"

# Подключаем раздачу статики для видео и других ассетов алфавита
if os.path.exists("alphabet"):
    app.mount("/alphabet", StaticFiles(directory="alphabet"), name="alphabet")

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

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Index.html not found</h1>"

# Исправлен путь на /api/subscription, чтобы совпадать с запросом из index.html
@app.get("/api/subscription")
async def check_subscription(user_id: int = Query(...)):
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
        
        # Возвращаем дату в формате с дефисами для фронтенда
        return {"active": True, "expires_at": expires_str, "is_trial": True}

    expires_at_str, status = row
    
    # Парсим строку из базы
    dt_obj = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
    
    # Для отображения пользователю можно оставить с точками, но в ответе лучше передавать исходную строку или раздельно
    conn.close()
    
    if dt_obj > datetime.now():
        return {"active": True, "expires_at": expires_at_str, "is_trial": (status == 'trial')}
    else:
        return {"active": False, "message": "Subscription expired"}