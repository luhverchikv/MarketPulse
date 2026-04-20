# main.py
import asyncio
from aiogram import Bot, Dispatcher
from config import config
#from db import init_db

from menu import router as menu_router
from api.youtube import router as youtube_router
from handlers.google_trends import router as google_trends_router

async def main():
    bot = Bot(token=config.bot.token)
    dp = Dispatcher()
    dp.include_router(menu_router)
    dp.include_router(youtube_router)
    dp.include_router(google_trends_router)
    
    # Запуск поллинга
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")

