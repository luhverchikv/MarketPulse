import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from db import init_db
from menu import start, handle_buttons
from scheduler import setup_scheduler

def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬТЕ_ТОКЕН_СЮДА")
    
    init_db()
    setup_scheduler(BOT_TOKEN)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

