# main.py
import asyncio
from aiogram import Bot, Dispatcher
#from aiogram.client.default import DefaultBotProperties
#from aiogram.enums import ParseMode

from config import config
#from db import init_db
from menu import router as menu_router
#from scheduler import scheduler_worker




#async def on_startup(bot: Bot):
    #"""Выполняется при запуске бота"""
    #init_db()
    #print(f"✅ {config.app.project_name} запущен | БД: {DB_FULL_PATH}")
    
    # Запускаем планировщик в фоне
    #if config.scheduler.enabled:
        #asyncio.create_task(
            #scheduler_worker(bot, config.scheduler.daily_digest_time)
        #)


async def main():
    bot = Bot(token=config.bot.token)
    dp = Dispatcher()
    dp.include_router(menu_router)
    dp.startup.register(on_startup)
    
    # Запуск поллинга
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")

