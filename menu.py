from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import save_user

TERRITORIES = {"🇷🇺 RU": "RU", "🇺🇸 US": "US", "🇪🇺 EU": "EU", "🇬🇧 GB": "GB"}
TOPICS = {"🤖 AI / Tech", "💰 Finance", "🛒 E-commerce", "🎮 Gaming"}
PERIODS = {"📅 1 день": "1d", "📆 7 дней": "7d", "📆 14 дней": "14d", "📆 30 дней": "30d"}

user_config = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(k, callback_data=f"set_{v}")] for k, v in TERRITORIES.items()]
    await update.message.reply_text("Выберите территорию для мониторинга:", reply_markup=InlineKeyboardMarkup(keyboard))
    user_config[update.message.chat_id] = {'step': 'territory'}

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if chat_id not in user_config:
        return

    cfg = user_config[chat_id]
    data = query.data

    if cfg['step'] == 'territory':
        cfg['territory'] = data.replace("set_", "")
        keyboard = [[InlineKeyboardButton(t, callback_data=f"topic_{t}")] for t in TOPICS]
        await query.edit_message_text("Выберите тему/нишу:", reply_markup=InlineKeyboardMarkup(keyboard))
        cfg['step'] = 'topic'

    elif cfg['step'] == 'topic':
        cfg['topic'] = data.replace("topic_", "")
        keyboard = [[InlineKeyboardButton(k, callback_data=f"per_{v}")] for k, v in PERIODS.items()]
        await query.edit_message_text("Выберите период анализа:", reply_markup=InlineKeyboardMarkup(keyboard))
        cfg['step'] = 'period'

    elif cfg['step'] == 'period':
        cfg['period'] = data.replace("per_", "")
        save_user(chat_id, cfg['territory'], cfg['topic'], cfg['period'])
        await query.edit_message_text(
            f"✅ Настройки сохранены!\n\n"
            f"Территория: {cfg['territory']}\n"
            f"Тема: {cfg['topic']}\n"
            f"Период: {cfg['period']}\n\n"
            f"Рассылка работает ежедневно. Используйте /config для изменения."
        )
        del user_config[chat_id]

