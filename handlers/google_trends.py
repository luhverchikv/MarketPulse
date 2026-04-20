# handlers/google_trends.py
"""
Хендлер для Google Trends в MarketPulse
"""

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from api.google_trends import fetch_google_trends

router = Router()


async def fetch_and_send_trends(
    message: types.Message,
    region_code: str,
    topic: str,
    period: str
):
    """
    Загрузка и отправка трендов из Google Trends.
    Это обычная функция, а не хендлер — вызывается из других хендлеров.
    """
    
    # Индикатор загрузки
    loading_msg = await message.answer("⏳ Анализирую Google Trends...")
    
    # Вызов API
    result = fetch_google_trends(
        region=region_code,
        topic=topic,
        period=period,
        max_results=10
    )
    
    # Удаляем индикатор
    await loading_msg.delete()
    
    # Обработка ошибки
    if not result["success"]:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Другая платформа", callback_data="back_to_platforms")]
        ])
        
        await message.answer(
            f"❌ <b>Ошибка Google Trends</b>\n\n"
            f"<code>{result['error']}</code>\n\n"
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
    
    text = (
        f"🔍 <b>Google Trends — {topic}</b>\n"
        f"🌍 Регион: <code>{region_code}</code> | 📅 Период: <code>{period_label}</code>\n"
        f"📊 Найдено запросов: {result['page_info']['total_results']}\n\n"
        f"<i>Топ связанных запросов по интересу:</i>\n\n"
    )
    
    # Добавляем топ-запросы
    for i, item in enumerate(result["items"], 1):
        emoji = "🔥" if item["volume"] >= 80 else "📈" if item["volume"] >= 50 else "📊"
        text += (
            f"{emoji} {i}. <b>{item['query']}</b>\n"
            f"   📈 Интерес: <code>{item['volume']}</code>\n"
            f"   🔗 <a href='{item['link']}'>Открыть в Google Trends</a>\n\n"
        )
    
    # Кнопка "Назад к платформам"
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другая платформа", callback_data="back_to_platforms")]
    ])
    
    # Telegram лимит: 4096 символов. Разбиваем на части.
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    
    for idx, chunk in enumerate(chunks):
        # Кнопку добавляем только к первому сообщению
        await message.answer(
            chunk,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_kb if idx == 0 else None
        )


@router.callback_query(F.data == "plat_google")
async def cb_google_selected(callback: types.CallbackQuery, state: FSMContext):
    """
    Хендлер: пользователь выбрал платформу Google Trends.
    Получает данные из FSM и вызывает fetch_and_send_trends.
    """
    data = await state.get_data()
    
    # Проверяем, есть ли настройки пользователя
    if not all(k in data for k in ['territory', 'topic', 'period']):
        await callback.answer("⚠️ Сначала настройте параметры через /start", show_alert=True)
        return
    
    await callback.answer(f"Загрузка: {data['topic']}")
    
    # Вызываем функцию отправки
    await fetch_and_send_trends(
        message=callback.message,
        region_code=data['territory'],
        topic=data['topic'],
        period=data['period']
    )
