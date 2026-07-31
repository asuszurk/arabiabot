from fastapi import FastAPI
import sqlite3
from datetime import datetime, timedelta

# Инициализация FastAPI приложения
app = FastAPI()

DB_NAME = "learning_bot.db"

@app.get("/api/check-subscription/{user_id}")
async def check_subscription(user_id: int):
    """
    Проверка подписки. Новым пользователям автоматически дается 3 дня триала.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expires_at, status FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        # Новый пользователь — даем ровно 3 суток пробного периода
        expires_at = datetime.now() + timedelta(days=3)
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO subscriptions (user_id, expires_at, status)
            VALUES (?, ?, 'trial')
        """, (user_id, expires_str))
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