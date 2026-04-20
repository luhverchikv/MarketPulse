# menu.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
#from db import save_user

router = Router()

# Константы меню
TERRITORIES = {"🇷🇺 RU": "RU", "🇺🇸 US": "US", "🇪🇺 EU": "EU", "🇬🇧 GB": "GB"}
TOPICS = ["🤖 AI / Tech", "💰 Finance", "🛒 E-commerce", "🎮 Gaming"]
PERIODS = {"📅 1 день": "1d", "📆 7 дней": "7d", "📆 14 дней": "14d", "📆 30 дней": "30d"}


# Состояния для FSM (если захотим расширить функционал)
class SetupStates:
    territory = "setup:territory"
    topic = "setup:topic"
    period = "setup:period"


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет!")
    

@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=k, callback_data=f"set_{v}")] 
        for k, v in TERRITORIES.items()
    ])
    await message.answer("🌍 **Выберите территорию для мониторинга:**", reply_markup=keyboard)
    await state.set_state(SetupStates.territory)


@router.callback_query(F.data.startswith("set_"))
async def cb_territory(callback: CallbackQuery, state: FSMContext):
    territory = callback.data.replace("set_", "")
    await state.update_data(territory=territory)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=f"topic_{t}")] 
        for t in TOPICS
    ])
    await callback.message.edit_text("🏷 **Выберите тему/нишу:**", reply_markup=keyboard)
    await state.set_state(SetupStates.topic)


@router.callback_query(F.data.startswith("topic_"))
async def cb_topic(callback: CallbackQuery, state: FSMContext):
    topic = callback.data.replace("topic_", "")
    await state.update_data(topic=topic)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=k, callback_data=f"per_{v}")] 
        for k, v in PERIODS.items()
    ])
    await callback.message.edit_text("📅 **Выберите период анализа:**", reply_markup=keyboard)
    await state.set_state(SetupStates.period)


@router.callback_query(F.data.startswith("per_"))
async def cb_period(callback: CallbackQuery, state: FSMContext):
    period = callback.data.replace("per_", "")
    data = await state.get_data()
    
    # Сохраняем настройки в БД
    #save_user(
        #chat_id=callback.from_user.id,
        #territory=data['territory'],
        #topic=data['topic'],
        #period=period
    #)
    
    await callback.message.edit_text(
        f"✅ **Настройки сохранены!**\n\n"
        f"🌍 Территория: `{data['territory']}`\n"
        f"🏷 Тема: `{data['topic']}`\n"
        f"📅 Период: `{period}`\n\n"
        f"📨 Рассылка работает ежедневно в 09:00.\n"
        f"Используйте /config для изменения настроек.",
        parse_mode="Markdown"
    )
    await state.clear()


