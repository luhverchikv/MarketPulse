# handlers/vk_trends.py
"""
Хендлер для VKontakte трендов в MarketPulse с FSM-потоком
"""

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from api.vk import (
    fetch_popular_posts,
    fetch_video_trending,
    fetch_vk_search,
    VK_COMMUNITIES,
    VK_TRENDING_TOPICS
)

router = Router()

# === FSM States ===
class VKTrendsForm(StatesGroup):
    waiting_for_mode = State()      # Выбор режима
    waiting_for_community = State() # Выбор сообщества
    waiting_for_search = State()    # Ввод поискового запроса


# =============================================================================
# Конфигурация
# =============================================================================
MODES = {
    "🔥 Тренды": "trending",
    "🎬 Видео": "video",
    "🔍 Поиск": "search",
    "📺 Сообщества": "communities",
}


# =============================================================================
# Клавиатуры
# =============================================================================
def create_mode_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора режима"""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"vk_mode_{code}")]
        for name, code in MODES.items()
    ]
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="vk_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_community_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора сообщества"""
    keyboard = []

    # Группируем по категориям
    for category, communities in VK_COMMUNITIES.items():
        keyboard.append([InlineKeyboardButton(
            text=f"📂 {category}",
            callback_data=f"vk_cat_{category}"
        )])

    # Быстрый выбор
    quick = list(VK_COMMUNITIES.values())[0]  # Берем первую категорию
    for name, _ in list(quick.items())[:4]:
        keyboard.append([
            InlineKeyboardButton(text=f"🔵 {name}", callback_data=f"vk_com_{name}")
        ])

    keyboard.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="vk_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# =============================================================================
# Формирование сообщений
# =============================================================================
def format_post_message(item: dict, index: int) -> str:
    """Форматирование поста"""
    emoji = "🔥" if index <= 3 else "📌"
    pinned = "📌 " if item.get("is_pinned") else ""

    text = item.get("text", "Без текста")
    if len(text) > 150:
        text = text[:147] + "..."

    result = (
        f"{emoji} <b>{pinned}{index}.</b>\n"
        f"   {text}\n"
        f"   👍 {item.get('likes', '0')} | 🔁 {item.get('reposts', '0')} | 💬 {item.get('comments', '0')}\n"
        f"   🔗 <a href='{item.get('url', '#')}'>Открыть</a>\n"
    )

    return result


def format_video_message(item: dict) -> str:
    """Форматирование видео"""
    return (
        f"🎬 <b>{item['title']}</b>\n"
        f"   👁️ {item['views']} просмотров | ⏱️ {item['duration']}\n"
        f"   👤 {item['author']}\n"
        f"   🔗 <a href='{item['url']}'>Смотреть</a>\n"
    )


def format_community_message(community: str, name: str) -> str:
    """Форматирование сообщества"""
    return (
        f"🔵 <b>{name}</b>\n"
        f"   👤 @{community}\n"
        f"   🔗 <a href='https://vk.com/{community}'>Открыть</a>\n"
    )


async def send_posts(message: types.Message, items: list, title: str = "VK Тренды"):
    """Отправка постов"""
    if not items:
        await message.answer("❌ Посты не найдены")
        return

    text = f"🔥 <b>{title}</b>\n\n"

    for i, item in enumerate(items, 1):
        text += format_post_message(item, i) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="vk_mode_trending"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


async def send_videos(message: types.Message, items: list):
    """Отправка видео"""
    if not items:
        await message.answer("❌ Видео не найдены")
        return

    text = "🎬 <b>Популярные видео VK</b>\n\n"

    for item in items:
        text += format_video_message(item) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="vk_mode_video"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


async def send_communities(message: types.Message, category: str = None):
    """Отправка списка сообществ"""
    text = "📺 <b>Популярные сообщества VK</b>\n\n"

    if category and category in VK_COMMUNITIES:
        communities = VK_COMMUNITIES[category]
        text += f"📂 Категория: {category}\n\n"
    else:
        # Все сообщества
        communities = {}
        for cat_communities in VK_COMMUNITIES.values():
            communities.update(cat_communities)

    for name, display in list(communities.items())[:10]:
        text += format_community_message(name, display) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📺 Другие", callback_data="vk_mode_communities"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=back_kb)


async def send_search_results(message: types.Message, items: list, query: str):
    """Отправка результатов поиска"""
    if not items:
        await message.answer("❌ Ничего не найдено")
        return

    text = f"🔍 <b>Результаты поиска: {query}</b>\n\n"

    for item in items:
        text += (
            f"📌 <b>{item['title']}</b>\n"
            f"   📊 {item.get('posts_count', 'N/A')} постов\n"
            f"   🔗 <a href='{item['url']}'>Найти</a>\n\n"
        )

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Новый поиск", callback_data="vk_mode_search"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


# =============================================================================
# Хендлеры
# =============================================================================
@router.callback_query(F.data == "plat_vk")
async def cb_vk_selected(callback: types.CallbackQuery, state: FSMContext):
    """Начало FSM-потока: выбор режима"""
    await state.clear()
    await state.set_state(VKTrendsForm.waiting_for_mode)

    await callback.message.edit_text(
        "🔵 <b>VKontakte Тренды</b>\n\n"
        "Выберите режим:\n\n"
        "🔥 <b>Тренды</b> — популярные посты\n"
        "🎬 <b>Видео</b> — популярные видео\n"
        "🔍 <b>Поиск</b> — найти по запросу\n"
        "📺 <b>Сообщества</b> — популярные группы\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=create_mode_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "vk_start")
async def cb_vk_restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск выбора режима"""
    await cb_vk_selected(callback, state)


@router.callback_query(F.data == "vk_cancel", StateFilter(VKTrendsForm))
async def cb_cancel_vk(callback: types.CallbackQuery, state: FSMContext):
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
    F.data == "vk_mode_trending",
    VKTrendsForm.waiting_for_mode
)
async def cb_vk_trending_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим трендов"""
    await callback.message.edit_text("⏳ Загружаю тренды VK...")

    result = fetch_popular_posts(count=10)

    await callback.message.delete()

    if result["success"]:
        await send_posts(callback.message, result["items"], "🔥 VK Тренды")
    else:
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n{result.get('error', 'Не удалось загрузить')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="vk_start")
            ]])
        )

    await callback.answer()


# --- Режим: Видео ---
@router.callback_query(
    F.data == "vk_mode_video",
    VKTrendsForm.waiting_for_mode
)
async def cb_vk_video_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим видео"""
    await callback.message.edit_text("⏳ Загружаю популярные видео...")

    result = fetch_video_trending(count=10)

    await callback.message.delete()

    if result["success"]:
        await send_videos(callback.message, result["items"])
    else:
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n{result.get('error', 'Не удалось загрузить')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="vk_start")
            ]])
        )

    await callback.answer()


# --- Режим: Поиск ---
@router.callback_query(
    F.data == "vk_mode_search",
    VKTrendsForm.waiting_for_mode
)
async def cb_vk_search_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим поиска"""
    await state.update_data(mode="search")
    await state.set_state(VKTrendsForm.waiting_for_search)

    await callback.message.edit_text(
        "🔍 <b>Поиск в VK</b>\n\n"
        "Введите поисковый запрос:\n\n"
        "Например:\n"
        "• `нейросети`\n"
        "• `Apple iPhone`\n"
        "• `Telegram боты`",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data="vk_cancel")
        ]])
    )
    await callback.answer()


@router.message(VKTrendsForm.waiting_for_search)
async def process_vk_search(message: types.Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("⚠️ Запрос слишком короткий")
        return

    await state.clear()

    loading = await message.answer("🔍 Ищу...")

    result = fetch_vk_search(query=query, count=10)

    await loading.delete()

    if result["success"]:
        await send_search_results(message, result["items"], query)
    else:
        await message.answer(
            f"❌ <b>Ошибка поиска</b>\n\n{result.get('error', 'Не удалось найти')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="vk_start")
            ]])
        )


# --- Режим: Сообщества ---
@router.callback_query(
    F.data == "vk_mode_communities",
    VKTrendsForm.waiting_for_mode
)
async def cb_vk_communities_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим сообществ"""
    await callback.message.edit_text("⏳ Загружаю список сообществ...")

    await callback.message.delete()

    await send_communities(callback.message)

    await callback.answer()


# --- Обработка текста в неправильном состоянии ---
@router.message(VKTrendsForm.waiting_for_community)
async def handle_wrong_input_community(message: types.Message):
    """Если прислали текст"""
    await message.answer(
        "⚠️ Пожалуйста, выберите сообщество из кнопок",
        reply_markup=create_community_keyboard()
    )