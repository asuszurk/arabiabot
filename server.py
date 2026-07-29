import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Определяем базовую директорию проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# Путь к папке с видеоуроками 
alphabet_path = os.path.join(BASE_DIR, "alphabet")

# Подключаем всю текущую папку для раздачи сайта и статики (index.html, видео и т.д.)
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)