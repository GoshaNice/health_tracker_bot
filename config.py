import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

# Чтение токена из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")
OPENWHEATHER_TOKEN = os.getenv("OPENWHEATHER_TOKEN")

if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

if not OPENWHEATHER_TOKEN:
    raise ValueError("Переменная окружения OPENWHEATHER_TOKEN не установлена!")
