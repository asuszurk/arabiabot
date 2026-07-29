import os
import sqlite3
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Определяем базовую директорию проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "learning_bot.db")

app = FastAPI()

# Добавляем CORS, чтобы запросы из Telegram Mini App не блокировались браузером
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любых доменов
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все HTTP-методы (GET, POST и т.д.)
    allow_headers=["*"],  # Разрешаем любые заголовки
)

def init_db():
    """Инициализация базы данных для подписок (не перезаписывает существующие таблицы)"""
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

# Инициализируем БД при старте сервера
init_db()

@app.post("/webhook/payment")
async def payment_webhook(request: Request):
    """
    Эндпоинт для приема уведомлений от платежной системы (Robokassa / ЮKassa) 
    при успешной оплате подписки (300 руб.)
    """
    data = await request.json()
    user_id = data.get("user_id")
    amount = data.get("amount")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not provided")
        
    if float(amount) < 300:
        raise HTTPException(status_code=400, detail="Invalid amount")

    # Продлеваем подписку ровно на 30 дней от текущего момента
    expires_at = datetime.now() + timedelta(days=30)
    expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO subscriptions (user_id, expires_at, status)
        VALUES (?, ?, 'active')
        ON CONFLICT(user_id) DO UPDATE SET
            expires_at = excluded.expires_at,
            status = 'active'
    """, (user_id, expires_str))
    conn.commit()
    conn.close()

    return {"status": "success", "message": f"Subscription activated for user {user_id} until {expires_str}"}

@app.get("/api/check-subscription/{user_id}")
async def check_subscription(user_id: int):
    """
    Эндпоинт для проверки статуса подписки конкретного пользователя из Mini App
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expires_at, status FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"active": False, "message": "No subscription found"}

    expires_at_str, status = row
    expires_at = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
    
    if status == 'active' and expires_at > datetime.now():
        return {"active": True, "expires_at": expires_at_str}
    else:
        return {"active": False, "message": "Subscription expired"}

# Путь к папке с видеоуроками 
alphabet_path = os.path.join(BASE_DIR, "alphabet")

# Подключаем всю текущую папку для раздачи сайта и статики (index.html, видео и т.д.)
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)