import schedule
import time
import threading
from api import fetch_all_trends
from db import get_active_users, save_trends
from telegram import Bot

bot_instance = None

def setup_scheduler(token: str):
    global bot_instance
    bot_instance = Bot(token=token)
    # Ежедневная рассылка в 09:00. Для PM-аудитории это оптимальный формат дайджеста
    schedule.every().day.at("09:00").do(_run_daily_digest)
    threading.Thread(target=_scheduler_loop, daemon=True).start()

def _scheduler_loop():
    while True:
        schedule.run_pending()
        time.sleep(60)

def _run_daily_digest():
    users = get_active_users()
    for chat_id, territory, topic, period in users:
        try:
            trends = fetch_all_trends(territory, topic, period)
            
            for source, items in trends.items():
                save_trends(chat_id, source, items)

            msg = f"📊 TrendScope Daily\n🌍 {territory} | 🏷 {topic} | 📅 {period}\n\n"
            for source, items in trends.items():
                msg += f"🔹 {source.upper()}:\n"
                for item in items[:3]:
                    if 'views' in item:
                        msg += f"• {item['title']} ({item['views']:,} 👁️)\n"
                    else:
                        msg += f"• {item['title']} (интерес: {item['volume']:,})\n"
                msg += "\n"
            
            bot_instance.send_message(chat_id=chat_id, text=msg)
        except Exception:
            pass  # Без логирования по ТЗ

