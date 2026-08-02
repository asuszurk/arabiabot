import os
from fastapi import FastAPI, Query, Request
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
@app.get("/api/create-payment")
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
        # Автоматический вебхук-адрес для уведомлений от ЮKassa
        "notification_url": "https://arabiabot-production.up.railway.app/api/yookassa-webhook",
        "capture": True,
        "description": f"Оплата подписки ArabiaBot (User ID: {user_id})",
        "metadata": {
            "user_id": user_id
        }
    })
    return {"confirmation_url": payment.confirmation.confirmation_url}

# Эндпоинт для приема вебхуков (уведомлений) от ЮKassa об успешной оплате
@app.post("/api/yookassa-webhook")
async def yookassa_webhook(request: Request):
    event_json = await request.json()
    
    # Проверяем, что платеж успешно завершен
    if event_json.get("event") == "payment.succeeded":
        payment_object = event_json.get("object", {})
        metadata = payment_object.get("metadata", {})
        user_id = metadata.get("user_id")
        
        if user_id:
            user_id = int(user_id)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Проверяем текущий срок подписки в базе
            cursor.execute("SELECT expires_at FROM subscriptions WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
            
            now = datetime.now()
            if row and row[0]:
                current_expires = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                # Если подписка еще активна, суммируем дни, иначе отсчитываем от текущего момента
                base_date = current_expires if current_expires > now else now
            else:
                base_date = now
                
            new_expires = base_date + timedelta(days=30)
            new_expires_str = new_expires.strftime("%Y-%m-%d %H:%M:%S")
            
            # Продлеваем или создаем премиум-подписку на 30 дней
            cursor.execute("""
                INSERT INTO subscriptions (user_id, expires_at, status) 
                VALUES (%s, %s, 'active')
                ON CONFLICT (user_id) 
                DO UPDATE SET expires_at = EXCLUDED.expires_at, status = 'active'
            """, (user_id, new_expires_str))
            
            conn.commit()
            cursor.close()
            conn.close()
            
    return {"status": "ok"}