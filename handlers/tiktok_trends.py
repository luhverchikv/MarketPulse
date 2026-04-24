# handlers/tiktok_trends.py
"""
Хендлер для TikTok трендов в MarketPulse с FSM-потоком
"""

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from api.tiktok import (
    fetch_tiktok_trending,
    fetch_tiktok_hashtags,
    fetch_tiktok_music_trending,
    fetch_tiktok_creator_trending,
    TIKTOK_REGIONS,
    TREND_CATEGORIES
)

router = Router()

# === FSM States ===
class TikTokTrendsForm(StatesGroup):
    waiting_for_mode = State()      # Выбор режима
    waiting_for_region = State()     # Выбор региона
    waiting_for_category = State()   # Выбор категории


# =============================================================================
# Конфигурация
# =============================================================================
MODES = {
    "🔥 Тренды": "trending",
    "🏷️ Хэштеги": "hashtags",
    "🎵 Музыка": "music",
    "👤 Креаторы": "creators",
}


# =============================================================================
# Клавиатуры
# =============================================================================
def create_mode_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора режима"""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"tiktok_mode_{code}")]
        for name, code in MODES.items()
    ]
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="tiktok_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_region_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора региона"""
    keyboard = []
    region_items = list(TIKTOK_REGIONS.items())

    for i in range(0, len(region_items), 2):
        row = []
        for name, code in region_items[i:i+2]:
            row.append(InlineKeyboardButton(
                text=name,
                callback_data=f"tiktok_region_{code}"
            ))
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="tiktok_back_to_mode"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="tiktok_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории"""
    keyboard = []
    cat_items = list(TREND_CATEGORIES.items())

    for i in range(0, len(cat_items), 2):
        row = []
        for name, code in cat_items[i:i+2]:
            row.append(InlineKeyboardButton(
                text=name,
                callback_data=f"tiktok_cat_{code}"
            ))
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(text="🔙 К регионам", callback_data="tiktok_back_to_region"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="tiktok_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# =============================================================================
# Формирование сообщений
# =============================================================================
def format_hashtag_message(item: dict, index: int) -> str:
    """Форматирование хэштега"""
    emoji = "🔥" if index <= 3 else "📊"
    return (
        f"{emoji} <b>#{item['name']}</b>\n"
        f"   👁️ {item.get('views', 'N/A')} просмотров\n"
        f"   📹 {item.get('posts', 'N/A')} видео\n"
        f"   🔗 <a href='{item['url']}'>Открыть</a>\n"
    )


def format_music_message(item: dict) -> str:
    """Форматирование музыки"""
    return (
        f"🎵 <b>{item['title']}</b>\n"
        f"   👤 {item['artist']}\n"
        f"   📹 {item['uses']} видео\n"
        f"   🔗 <a href='{item['url']}'>Слушать</a>\n"
    )


def format_creator_message(item: dict) -> str:
    """Форматирование креатора"""
    return (
        f"👤 <b>@{item['username']}</b>\n"
        f"   📛 {item['name']}\n"
        f"   👥 {item['followers']} подписчиков\n"
        f"   🔗 <a href='{item['url']}'>Профиль</a>\n"
    )


def format_trending_video(item: dict, index: int) -> str:
    """Форматирование видео"""
    emoji = "🔥" if index <= 3 else "📱"

    # Формируем текст
    title = item.get('title', 'Без описания')
    if len(title) > 80:
        title = title[:77] + "..."

    text = (
        f"{emoji} <b>{index}. {title}</b>\n"
        f"   👤 @{item.get('author', 'unknown')}\n"
        f"   👍 {item.get('likes', '0')} | 💬 {item.get('comments', '0')} | 🔁 {item.get('shares', '0')}\n"
    )

    if item.get('music'):
        text += f"   🎵 {item['music'][:40]}\n"

    if item.get('hashtags'):
        hashtags = " ".join([f"#{h}" for h in item['hashtags'][:5]])
        text += f"   {hashtags}\n"

    text += f"   🔗 <a href='{item['url']}'>Смотреть</a>\n"

    return text


async def send_hashtags(message: types.Message, items: list):
    """Отправка хэштегов"""
    if not items:
        await message.answer("❌ Хэштеги не найдены")
        return

    text = "🏷️ <b>Популярные хэштеги TikTok</b>\n\n"

    for i, item in enumerate(items, 1):
        text += format_hashtag_message(item, i) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="tiktok_mode_hashtags"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    # Разбиваем на части
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


async def send_music(message: types.Message, items: list):
    """Отправка музыки"""
    if not items:
        await message.answer("❌ Музыка не найдена")
        return

    text = "🎵 <b>Популярная музыка TikTok</b>\n\n"

    for item in items:
        text += format_music_message(item) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="tiktok_mode_music"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


async def send_creators(message: types.Message, items: list):
    """Отправка креаторов"""
    if not items:
        await message.answer("❌ Креаторы не найдены")
        return

    text = "👤 <b>Топ креаторы TikTok</b>\n\n"

    for item in items:
        text += format_creator_message(item) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="tiktok_mode_creators"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


async def send_trending_videos(message: types.Message, items: list, region: str):
    """Отправка трендовых видео"""
    if not items:
        await message.answer("❌ Видео не найдены")
        return

    region_name = [k for k, v in TIKTOK_REGIONS.items() if v == region]
    region_name = region_name[0] if region_name else region

    text = f"🔥 <b>Тренды TikTok</b>\n"
    text += f"🌍 Регион: {region_name}\n"
    text += f"📈 Видео: {len(items)}\n\n"

    for i, item in enumerate(items, 1):
        text += format_trending_video(item, i) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Другие регионы", callback_data="tiktok_back_to_region"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


# =============================================================================
# Хендлеры
# =============================================================================
@router.callback_query(F.data == "plat_tiktok")
async def cb_tiktok_selected(callback: types.CallbackQuery, state: FSMContext):
    """Начало FSM-потока: выбор режима"""
    await state.clear()
    await state.set_state(TikTokTrendsForm.waiting_for_mode)

    await callback.message.edit_text(
        "🎵 <b>TikTok Тренды</b>\n\n"
        "Выберите режим:\n\n"
        "🔥 <b>Тренды</b> — популярные видео\n"
        "🏷️ <b>Хэштеги</b> — что в тренде\n"
        "🎵 <b>Музыка</b> — популярные треки\n"
        "👤 <b>Креаторы</b> — топ блогеры\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=create_mode_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "tiktok_start")
async def cb_tiktok_restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск выбора режима"""
    await cb_tiktok_selected(callback, state)


@router.callback_query(F.data == "tiktok_cancel", StateFilter(TikTokTrendsForm))
async def cb_cancel_tiktok(callback: types.CallbackQuery, state: FSMContext):
    """Отмена операции"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Операция отменена",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_platforms")
        ]])
    )
    await callback.answer()


# --- Режим: Тренды ---
@router.callback_query(
    F.data == "tiktok_mode_trending",
    TikTokTrendsForm.waiting_for_mode
)
async def cb_tiktok_trending_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим трендов — выбор региона"""
    await state.update_data(mode="trending")
    await state.set_state(TikTokTrendsForm.waiting_for_region)

    await callback.message.edit_text(
        "🔥 <b>Тренды TikTok</b>\n\n"
        "Выберите регион:",
        parse_mode="HTML",
        reply_markup=create_region_keyboard()
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("tiktok_region_"),
    TikTokTrendsForm.waiting_for_region
)
async def cb_tiktok_region(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора региона"""
    region = callback.data.replace("tiktok_region_", "")
    data = await state.get_data()

    await callback.message.edit_text("⏳ Загружаю тренды...")

    # Для трендов
    if data.get("mode") == "trending":
        result = fetch_tiktok_trending(region=region, count=10)

        if result["success"] and result["items"]:
            await callback.message.delete()
            await send_trending_videos(callback.message, result["items"], region)
        elif result.get("items"):  # Есть fallback данные
            await callback.message.delete()
            await send_trending_videos(callback.message, result["items"], region)
        else:
            await callback.message.edit_text(
                f"❌ <b>Ошибка</b>\n\n{result.get('error', 'Не удалось загрузить')}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="tiktok_start")
                ]])
            )

    await callback.answer()


# --- Режим: Хэштеги ---
@router.callback_query(
    F.data == "tiktok_mode_hashtags",
    TikTokTrendsForm.waiting_for_mode
)
async def cb_tiktok_hashtags_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим хэштегов"""
    await callback.message.edit_text("⏳ Загружаю популярные хэштеги...")

    result = fetch_tiktok_hashtags(count=15)

    await callback.message.delete()

    if result["success"]:
        await send_hashtags(callback.message, result["items"])
    else:
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n{result.get('error', 'Не удалось загрузить')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="tiktok_start")
            ]])
        )

    await callback.answer()


# --- Режим: Музыка ---
@router.callback_query(
    F.data == "tiktok_mode_music",
    TikTokTrendsForm.waiting_for_mode
)
async def cb_tiktok_music_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим музыки"""
    await callback.message.edit_text("⏳ Загружаю популярную музыку...")

    result = fetch_tiktok_music_trending(count=10)

    await callback.message.delete()

    if result["success"]:
        await send_music(callback.message, result["items"])
    else:
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n{result.get('error', 'Не удалось загрузить')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="tiktok_start")
            ]])
        )

    await callback.answer()


# --- Режим: Креаторы ---
@router.callback_query(
    F.data == "tiktok_mode_creators",
    TikTokTrendsForm.waiting_for_mode
)
async def cb_tiktok_creators_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим креаторов"""
    await callback.message.edit_text("⏳ Загружаю топ креаторов...")

    result = fetch_tiktok_creator_trending(count=10)

    await callback.message.delete()

    if result["success"]:
        await send_creators(callback.message, result["items"])
    else:
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n{result.get('error', 'Не удалось загрузить')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="tiktok_start")
            ]])
        )

    await callback.answer()


# --- Навигация ---
@router.callback_query(F.data == "tiktok_back_to_mode")
async def cb_back_to_mode(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору режима"""
    await state.clear()
    await cb_tiktok_selected(callback, state)


@router.callback_query(F.data == "tiktok_back_to_region")
async def cb_back_to_region(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору региона"""
    data = await state.get_data()

    if data.get("mode") == "trending":
        await state.set_state(TikTokTrendsForm.waiting_for_region)
        await callback.message.edit_text(
            "🔥 <b>Тренды TikTok</b>\n\n"
            "Выберите регион:",
            parse_mode="HTML",
            reply_markup=create_region_keyboard()
        )

    await callback.answer()


# --- Обработка текста в неправильном состоянии ---
@router.message(TikTokTrendsForm.waiting_for_region)
async def handle_wrong_input_region(message: types.Message):
    """Если прислали текст вместо выбора региона"""
    await message.answer(
        "⚠️ Пожалуйста, выберите регион из кнопок:",
        reply_markup=create_region_keyboard()
    )