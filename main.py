# main.py
import asyncio
from aiogram import Bot, Dispatcher
from config import config
#from db import init_db

from menu import router as menu_router
from handlers.youtube_trends import router as youtube_router
from handlers.reddit_trends import router as reddit_trends_router
from handlers.yandex_trends import router as yandex_trends_router
from handlers.tiktok_trends import router as tiktok_trends_router


async def main():
    bot = Bot(token=config.bot.token)
    dp = Dispatcher()
    dp.include_router(menu_router)
    dp.include_router(youtube_router)
    dp.include_router(reddit_trends_router)
    dp.include_router(yandex_trends_router)
    dp.include_router(tiktok_trends_router)
    
    # Запуск поллинга
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")

