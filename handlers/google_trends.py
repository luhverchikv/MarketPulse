# handlers/google_trends.py
"""
Хендлер для Google Trends в MarketPulse с FSM-потоком
"""

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove

from api.google_trends import fetch_google_trends

router = Router()

# === FSM States ===
class GoogleTrendsForm(StatesGroup):
    waiting_for_topic = State()
    waiting_for_region = State()
    waiting_for_period = State()


# === Конфигурация опций ===
REGIONS = {
    "🇷🇺 Россия": "RU",
    "🇺🇸 США": "US",
    "🇬🇧 Великобритания": "GB",
    "🇩🇪 Германия": "DE",
    "🇫🇷 Франция": "FR",
    "🇮🇹 Италия": "IT",
    "🇪🇸 Испания": "ES",
    "🇧🇾 Беларусь": "BY",
    "🇰🇿 Казахстан": "KZ",
    "🇺🇦 Украина": "UA",
    "🌍 Весь мир": "",
}

PERIODS = {
    "⏱️ 24 часа": "1d",
    "📅 7 дней": "7d",
    "📆 14 дней": "14d",
    "🗓️ 30 дней": "30d",
}


def create_region_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с выбором региона"""
    keyboard = []
    region_items = list(REGIONS.items())
    for i in range(0, len(region_items), 2):
        row = []
        for name, code in region_items[i:i+2]:
            row.append(InlineKeyboardButton(text=name, callback_data=f"region_{code}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="gtrends_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_period_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с выбором периода"""
    keyboard = []
    period_items = list(PERIODS.items())
    for i in range(0, len(period_items), 2):
        row = []
        for name, code in period_items[i:i+2]:
            row.append(InlineKeyboardButton(text=name, callback_data=f"period_{code}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="gtrends_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def fetch_and_send_trends(
    message: types.Message,
    region_code: str,
    topic: str,
    period: str
):
    """
    Загрузка и отправка трендов из Google Trends.
    """
    loading_msg = await message.answer("⏳ Анализирую Google Trends...")

    result = fetch_google_trends(
        region=region_code,
        topic=topic,
        period=period,
        max_results=10
    )

    await loading_msg.delete()

    if not result["success"]:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="gtrends_start")
        ]])
        await message.answer(
            f"❌ **Ошибка Google Trends**\n\n"
            f"`{result['error']}`\n\n"
            "💡 Попробуйте:\n"
            "• Изменить тему на более общую (например, 'крипта')\n"
            "• Выбрать другой регион или период",
            parse_mode="HTML",
            reply_markup=back_kb
        )
        return

    # Формируем красивое сообщение
    period_labels = {"1d": "24ч", "7d": "7 дней", "14d": "14 дней", "30d": "30 дней"}
    period_label = period_labels.get(period, period)
    
    region_name = "Весь мир" if not region_code else [k for k, v in REGIONS.items() if v == region_code][0]

    text = (
        f"🔍 **Google Trends — {topic}**\n"
        f"🌍 Регион: `{region_name}` | 📅 Период: `{period_label}`\n"
        f"📊 Найдено запросов: {result['page_info']['total_results']}\n\n"
        f"_Топ связанных запросов по интересу:_\n\n"
    )

    for i, item in enumerate(result["items"], 1):
        emoji = "🔥" if item["volume"] >= 80 else "📈" if item["volume"] >= 50 else "📊"
        text += (
            f"{emoji} {i}. **{item['query']}**\n"
            f"   📈 Интерес: `{item['volume']}`\n"
            f"   🔗 [Открыть в Google Trends]({item['link']})\n\n"
        )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Новый поиск", callback_data="gtrends_start"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
    ]])

    # Разбиваем на части из-за лимита Telegram (4096 символов)
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]

    for idx, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_kb if idx == 0 else None
        )


# === Хендлеры ===

@router.callback_query(F.data == "plat_google")
async def cb_google_selected(callback: types.CallbackQuery, state: FSMContext):
    """Начало FSM-потока: запрос темы"""
    await state.clear()
    await state.set_state(GoogleTrendsForm.waiting_for_topic)
    
    await callback.message.edit_text(
        "🔍 **Введите поисковый запрос**\n\n"
        "Например:\n"
        "• `нейросети`\n"
        "• `криптовалюта`\n"
        "• `AI tools`\n\n"
        "Или нажмите ❌ для отмены",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data="gtrends_cancel")
        ]])
    )
    await callback.answer()


@router.callback_query(F.data == "gtrends_cancel", GoogleTrendsForm.waiting_for_topic | GoogleTrendsForm.waiting_for_region | GoogleTrendsForm.waiting_for_period)
async def cb_cancel_gtrends(callback: types.CallbackQuery, state: FSMContext):
    """Отмена FSM-потока"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Поиск отменён",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_platforms")
        ]])
    )
    await callback.answer()


@router.message(GoogleTrendsForm.waiting_for_topic)
async def process_topic(message: types.Message, state: FSMContext):
    """Обработка введённой темы и переход к выбору региона"""
    topic = message.text.strip()
    if len(topic) < 2:
        await message.answer("⚠️ Запрос слишком короткий. Введите минимум 2 символа.")
        return
    
    await state.update_data(topic=topic)
    await state.set_state(GoogleTrendsForm.waiting_for_region)
    
    await message.answer(
        "🌍 **Выберите регион**\n\n"
        "От этого зависит, какие тренды будут показаны:",
        reply_markup=create_region_keyboard()
    )


@router.callback_query(F.data.startswith("region_"), GoogleTrendsForm.waiting_for_region)
async def process_region(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора региона и переход к выбору периода"""
    region_code = callback.data.split("_")[1]
    await state.update_data(region=region_code)
    await state.set_state(GoogleTrendsForm.waiting_for_period)
    
    await callback.message.edit_text(
        "📅 **Выберите период анализа**\n\n"
        "Чем короче период — тем актуальнее тренды:",
        reply_markup=create_period_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("period_"), GoogleTrendsForm.waiting_for_period)
async def process_period(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора периода и запуск поиска"""
    period = callback.data.split("_")[1]
    data = await state.get_data()
    
    await state.clear()
    
    await callback.message.edit_text(
        "✅ Параметры приняты. Начинаю поиск...",
        reply_markup=None
    )
    await callback.answer()
    
    await fetch_and_send_trends(
        message=callback.message,
        region_code=data["region"],
        topic=data["topic"],
        period=period
    )


@router.message(GoogleTrendsForm.waiting_for_region | GoogleTrendsForm.waiting_for_period)
async def handle_wrong_input_during_selection(message: types.Message):
    """Обработка текстовых сообщений, когда ожидается нажатие кнопки"""
    await message.answer(
        "⚠️ Пожалуйста, используйте кнопки ниже для выбора.",
        reply_markup=create_region_keyboard() if await GoogleTrendsForm.waiting_for_region.get_state() == message.bot.state else create_period_keyboard()
    )

