import os
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import psycopg2
from datetime import datetime, timedelta
from yookassa import Configuration, Payment

app = FastAPI()

# Получаем ссылку на облачную базу данных из переменных окружения Railway
DATABASE_URL = os.environ.get("DATABASE_URL")

# Настройка учетных данных ЮKassa
Configuration.account_id = "1423542"
Configuration.secret_key = "live_4QYOa6BsX-p1hqoL1WS0vB6z6SamezpbjUDIUduOzSk"

# Подключаем раздачу статики для видео и других ассетов алфавита
if os.path.exists("alphabet"):
    app.mount("/alphabet", StaticFiles(directory="alphabet"), name="alphabet")

# Подключаем раздачу статики для файлов с данными
if os.path.exists("data"):
    app.mount("/data", StaticFiles(directory="data"), name="data")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id BIGINT PRIMARY KEY, 
            expires_at TEXT, 
            status TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Инициализируем таблицу при старте
init_db()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Index.html not found</h1>"

@app.get("/api/subscription")
async def check_subscription(user_id: int = Query(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT expires_at, status FROM subscriptions WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()

    if not row:
        expires_at = datetime.now() + timedelta(days=3)
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO subscriptions (user_id, expires_at, status) VALUES (%s, %s, 'trial')", (user_id, expires_str))
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"active": True, "expires_at": expires_str, "is_trial": True}

    expires_at_str, status = row
    dt_obj = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
    cursor.close()
    conn.close()
    
    if dt_obj > datetime.now():
        return {"active": True, "expires_at": expires_at_str, "is_trial": (status == 'trial')}
    else:
        return {"active": False, "message": "Subscription expired"}

# Эндпоинт для создания платежа через ЮKassa
@app.post("/api/create-payment")
async def create_payment(user_id: int):
    payment = Payment.create({
        "amount": {
            "value": "500.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/aribia2026_bot"
        },
        "capture": True,
        "description": f"Оплата подписки ArabiaBot (User ID: {user_id})",
        "metadata": {
            "user_id": user_id
        }
    })
    return {"confirmation_url": payment.confirmation.confirmation_url}