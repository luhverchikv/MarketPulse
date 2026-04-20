# scheduler.py
import asyncio
from aiogram import Bot
from api import fetch_all_trends
from db import get_active_users, save_trends
from config import config


async def send_daily_digest(bot: Bot):
    """Асинхронная функция рассылки"""
    users = get_active_users()
    
    for chat_id, territory, topic, period in users:
        try:
            trends = fetch_all_trends(territory, topic, period)
            
            # Сохраняем сырые данные
            for source, items in trends.items():
                save_trends(chat_id, source, items)

            # Формируем сообщение
            msg = f"📊 {config.app.project_name} Daily\n"
            msg += f"🌍 {territory} | 🏷 {topic} | 📅 {period}\n\n"
            
            for source, items in trends.items():
                emoji = "🔍" if source == "google" else "▶️"
                msg += f"{emoji} **{source.upper()}**:\n"
                for item in items[:3]:
                    if 'views' in item:
                        msg += f"• {item['title']} ({item['views']:,} 👁️)\n"
                    else:
                        msg += f"• {item['title']} (интерес: {item['volume']:,})\n"
                msg += "\n"
            
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            
        except Exception:
            pass  # Без логирования по ТЗ


async def scheduler_worker(bot: Bot, digest_time: str):
    """Бесконечный цикл проверки времени"""
    hour, minute = map(int, digest_time.split(":"))
    
    while True:
        now = asyncio.get_event_loop().time()
        # Вычисляем следующее время запуска (упрощённо)
        # Для продакшена лучше использовать APScheduler с timezone
        
        current_hour = int(asyncio.get_event_loop().time() // 3600 % 24)
        current_minute = int(asyncio.get_event_loop().time() // 60 % 60)
        
        if current_hour == hour and current_minute == minute:
            await send_daily_digest(bot)
            await asyncio.sleep(70)  # Ждём минуту, чтобы не сработать дважды
        
        await asyncio.sleep(30)  # Проверка каждые 30 секунд

