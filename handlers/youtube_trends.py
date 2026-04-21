# api/youtube.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from api.youtube import fetch_trending_videos
from config import config

router = Router()

# Категории YouTube
YOUTUBE_CATEGORIES = {
    "🎵 Музыка": "10",
    "🎮 Игры": "20",
    "🎬 Фильмы и анимация": "1",
    "🚗 Авто и транспорт": "2",
    "🐾 Животные": "15",
    "⚽ Спорт": "17",
    "✈️ Путешествия и события": "19",
    "👤 Люди и блоги": "22",
    "😂 Комедия": "23",
    "🎉 Развлечения": "24",
    "📰 Новости и политика": "25",
    "🧴 How-to и стиль": "26",
    "🎓 Образование": "27",
    "🔬 Наука и техника": "28",
    "📱 YouTube Shorts": "42",
    "📺 Шоу": "43",
    "🎞️ Трейлеры": "44"
}

# Регионы
YOUTUBE_REGIONS = {
    "🇷🇺 Россия": "RU",
    "🇺🇸 США": "US",
    "🇧🇾 Беларусь": "BY",
}


@router.callback_query(F.data == "plat_youtube")
async def cmd_youtube(callback: CallbackQuery):

    
    if not config.youtube.api_key:
        await callback.message.answer(
            "❌ <b>YouTube API ключ не настроен!</b>\n\n"
            "Добавьте <code>YOUTUBE_API_KEY</code> в .env"
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=cat, callback_data=f"yt_cat_{cat_id}")
            for cat, cat_id in list(YOUTUBE_CATEGORIES.items())[i:i+2]
        ]
        for i in range(0, len(YOUTUBE_CATEGORIES), 2)
    ])
    
    await callback.message.answer(
        "🎬 <b>YouTube Trends</b>\n\nВыберите категорию:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("yt_cat_"))
async def cb_youtube_category(callback: CallbackQuery):
    """Выбор категории"""
    category_id = callback.data.replace("yt_cat_", "")
    category_name = next(
        (name for name, cid in YOUTUBE_CATEGORIES.items() if cid == category_id),
        "Unknown"
    )
    
    await callback.answer(f"Загрузка: {category_name}")
    
    loading_msg = await callback.message.answer("⏳ Загружаю...")
    
    result = fetch_trending_videos(
        api_key=config.youtube.api_key,
        region_code="BY",  # type: ignore
        video_category_id=category_id,  # type: ignore
        max_results=10
    )
    
    await loading_msg.delete()
    
    if not result["success"]:
        await callback.message.answer(f"❌ Ошибка: {result['error']}")
        return
    
    text = (
        f"🎬 <b>{category_name}</b>\n"
        f"📊 Всего: {result['page_info']['total_results']}\n\n"
    )
    
    for i, video in enumerate(result["items"], 1):
        text += (
            f"{i}. <b>{video['title']}</b>\n"
            f"   👤 {video['channel']}\n"
            f"   👁️ {video['view_count']:,}\n"
            f"   👍 {video['like_count']:,}\n"
            f"   🔗 <a href='{video['url']}'>Смотреть</a>\n\n"
        )
    
    # Разбиваем на части если длинное
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await callback.message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)

