# handlers/google_trends.py
from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from api.google_trends import fetch_google_trends

router = Router()

async def fetch_and_send_trends(
    message: types.Message,
    region_code: str,
    topic: str,
    period: str
):
    """Загрузка и отправка трендов Google Trends"""
    
    loading_msg = await message.answer("⏳ Анализирую Google Trends...")
    
    result = fetch_google_trends(
        region=region_code,
        topic=topic,
        period=period,
        max_results=10
    )
    
    await loading_msg.delete()
    
    if not result["success"]:
        await message.answer(
            f"❌ <b>Ошибка Google Trends</b>\n\n"
            f"<code>{result['error']}</code>\n\n"
            "Попробуйте изменить тему или регион.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Другая платформа", callback_data="back_to_platforms")]
            ])
        )
        return
    
    # Формируем сообщение
    text = (
        f"🔍 <b>Google Trends — {topic}</b>\n"
        f"🌍 Регион: {region_code} | 📅 Период: {period}\n"
        f"📊 Найдено запросов: {result['page_info']['total_results']}\n\n"
    )
    
    for i, item in enumerate(result["items"], 1):
        text += (
            f"{i}. <b>{item['query']}</b>\n"
            f"   📈 Интерес: {item['volume']}\n"
            f"   🔗 <a href='{item['link']}'>Открыть в Trends</a>\n\n"
        )
    
    # Кнопка "Назад"
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другая платформа", callback_data="back_to_platforms")]
    ])
    
    # Разбиваем на части, если длинное
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(
            chunk,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_kb if chunk == text.split("\n\n")[0] else None
        )
