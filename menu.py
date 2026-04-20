# menu.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
#from db import save_user

router = Router()


PLATFORMS = {
    "▶️ YouTube": "youtube",
    "🔍 Google Trends": "google",
    # "🎵 TikTok": "tiktok",      # Заглушка на будущее
    # "🐦 X / Twitter": "twitter", # Заглушка на будущее
}

def get_platform_keyboard():
    """Клавиатура выбора платформы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"plat_{code}")]
        for name, code in PLATFORMS.items()
    ])


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    keyboard = get_platform_keyboard()
    
    await message.answer(
        f"👋 Привет, я <b>{config.app.project_name}</b>!\n\n"
        "Я помогаю отслеживать тренды на разных платформах.\n"
        "Выберите платформу для аналитики:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )