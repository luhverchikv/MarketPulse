# handlers/pinterest_trends.py
"""
Хендлер для Pinterest трендов в MarketPulse с FSM-потоком
"""

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from api.pinterest import (
    fetch_trending_keywords,
    fetch_popular_pins,
    fetch_pinterest_board_trends,
    search_pinterest,
    PINTEREST_REGIONS,
    PINTEREST_CATEGORIES
)

router = Router()

# === FSM States ===
class PinterestTrendsForm(StatesGroup):
    waiting_for_mode = State()      # Выбор режима
    waiting_for_region = State()    # Выбор региона
    waiting_for_category = State()  # Выбор категории
    waiting_for_search = State()    # Ввод поискового запроса


# =============================================================================
# Конфигурация
# =============================================================================
MODES = {
    "🔥 Ключевые слова": "keywords",
    "📌 Популярные пины": "pins",
    "📋 Трендовые доски": "boards",
    "🔍 Поиск": "search",
}


# =============================================================================
# Клавиатуры
# =============================================================================
def create_mode_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора режима"""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"pinterest_mode_{code}")]
        for name, code in MODES.items()
    ]
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="pinterest_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_region_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора региона"""
    keyboard = []
    region_items = list(PINTEREST_REGIONS.items())

    for i in range(0, len(region_items), 2):
        row = []
        for name, code in region_items[i:i+2]:
            row.append(InlineKeyboardButton(
                text=name,
                callback_data=f"pinterest_region_{code}"
            ))
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="pinterest_back_to_mode"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="pinterest_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории"""
    keyboard = []
    cat_items = list(PINTEREST_CATEGORIES.items())

    for i in range(0, len(cat_items), 2):
        row = []
        for name, code in cat_items[i:i+2]:
            row.append(InlineKeyboardButton(
                text=name,
                callback_data=f"pinterest_cat_{code}"
            ))
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(text="🔙 К регионам", callback_data="pinterest_back_to_region"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="pinterest_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# =============================================================================
# Формирование сообщений
# =============================================================================
def format_keyword_message(item: dict, index: int) -> str:
    """Форматирование ключевого слова"""
    emoji = "🔥" if index <= 3 else "📊"
    trend = item.get("trend_index", 0)

    return (
        f"{emoji} <b>{index}. {item['keyword']}</b>\n"
        f"   📈 Тренд: {trend}%\n"
        f"   📂 Категория: {item.get('category', 'N/A')}\n"
        f"   🔗 <a href='{item['url']}'>Смотреть</a>\n"
    )


def format_pin_message(item: dict) -> str:
    """Форматирование пина"""
    return (
        f"📌 <b>{item['title']}</b>\n"
        f"   💾 {item['saves']} сохранений\n"
        f"   📂 {item['category']} | 👤 {item['author']}\n"
        f"   🔗 <a href='{item['url']}'>Открыть</a>\n"
    )


def format_board_message(item: dict) -> str:
    """Форматирование доски"""
    return (
        f"📋 <b>{item['name']}</b>\n"
        f"   📌 {item['pins']} пинов | 👥 {item['followers']} подписчиков\n"
        f"   📂 {item['category']}\n"
        f"   🔗 <a href='{item['url']}'>Открыть</a>\n"
    )


def format_search_result(item: dict) -> str:
    """Форматирование результата поиска"""
    return (
        f"🔍 <b>{item['suggestion']}</b>\n"
        f"   📌 {item['pins']} пинов | 📂 {item['category']}\n"
        f"   🔗 <a href='{item['url']}'>Смотреть</a>\n"
    )


async def send_keywords(message: types.Message, items: list, region: str):
    """Отправка ключевых слов"""
    if not items:
        await message.answer("❌ Ключевые слова не найдены")
        return

    region_name = [k for k, v in PINTEREST_REGIONS.items() if v == region]
    region_name = region_name[0] if region_name else region

    text = f"🔑 <b>Pinterest Ключевые слова — {region_name}</b>\n\n"

    for i, item in enumerate(items, 1):
        text += format_keyword_message(item, i) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Другие регионы", callback_data="pinterest_back_to_region"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


async def send_pins(message: types.Message, items: list, category: str = None):
    """Отправка пинов"""
    if not items:
        await message.answer("❌ Пины не найдены")
        return

    cat_text = f" — {PINTEREST_CATEGORIES.get(category, category)}" if category else ""

    text = f"📌 <b>Популярные пины{cat_text}</b>\n\n"

    for item in items:
        text += format_pin_message(item) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Другие категории", callback_data="pinterest_mode_pins"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


async def send_boards(message: types.Message, items: list):
    """Отправка досок"""
    if not items:
        await message.answer("❌ Доски не найдены")
        return

    text = "📋 <b>Трендовые доски Pinterest</b>\n\n"

    for item in items:
        text += format_board_message(item) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="pinterest_mode_boards"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


async def send_search_results(message: types.Message, items: list, query: str):
    """Отправка результатов поиска"""
    if not items:
        await message.answer("❌ Ничего не найдено")
        return

    text = f"🔍 <b>Результаты поиска: {query}</b>\n\n"

    for item in items:
        text += format_search_result(item) + "\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Новый поиск", callback_data="pinterest_mode_search"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)


# =============================================================================
# Хендлеры
# =============================================================================
@router.callback_query(F.data == "plat_pinterest")
async def cb_pinterest_selected(callback: types.CallbackQuery, state: FSMContext):
    """Начало FSM-потока: выбор режима"""
    await state.clear()
    await state.set_state(PinterestTrendsForm.waiting_for_mode)

    await callback.message.edit_text(
        "📌 <b>Pinterest Тренды</b>\n\n"
        "Выберите режим:\n\n"
        "🔥 <b>Ключевые слова</b> — что ищут пользователи\n"
        "📌 <b>Популярные пины</b> — самые сохраняемые\n"
        "📋 <b>Трендовые доски</b> — топ коллекций\n"
        "🔍 <b>Поиск</b> — найти по запросу\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=create_mode_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "pinterest_start")
async def cb_pinterest_restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск выбора режима"""
    await cb_pinterest_selected(callback, state)


@router.callback_query(F.data == "pinterest_cancel", StateFilter(PinterestTrendsForm))
async def cb_cancel_pinterest(callback: types.CallbackQuery, state: FSMContext):
    """Отмена операции"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Операция отменена",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_platforms")
        ]])
    )
    await callback.answer()


# --- Режим: Ключевые слова ---
@router.callback_query(
    F.data == "pinterest_mode_keywords",
    PinterestTrendsForm.waiting_for_mode
)
async def cb_pinterest_keywords_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим ключевых слов — выбор региона"""
    await state.update_data(mode="keywords")
    await state.set_state(PinterestTrendsForm.waiting_for_region)

    await callback.message.edit_text(
        "🔥 <b>Ключевые слова Pinterest</b>\n\n"
        "Выберите регион:",
        parse_mode="HTML",
        reply_markup=create_region_keyboard()
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("pinterest_region_"),
    PinterestTrendsForm.waiting_for_region
)
async def cb_pinterest_region(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора региона"""
    region = callback.data.replace("pinterest_region_", "")
    data = await state.get_data()

    await callback.message.edit_text("⏳ Загружаю ключевые слова...")

    result = fetch_trending_keywords(region=region, count=15)

    await callback.message.delete()

    if result["success"]:
        await send_keywords(callback.message, result["items"], region)
    else:
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n{result.get('error', 'Не удалось загрузить')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="pinterest_start")
            ]])
        )

    await callback.answer()


# --- Режим: Популярные пины ---
@router.callback_query(
    F.data == "pinterest_mode_pins",
    PinterestTrendsForm.waiting_for_mode
)
async def cb_pinterest_pins_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим пинов — выбор категории"""
    await state.update_data(mode="pins")
    await state.set_state(PinterestTrendsForm.waiting_for_category)

    await callback.message.edit_text(
        "📌 <b>Популярные пины Pinterest</b>\n\n"
        "Выберите категорию:",
        parse_mode="HTML",
        reply_markup=create_category_keyboard()
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("pinterest_cat_"),
    PinterestTrendsForm.waiting_for_category
)
async def cb_pinterest_category(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора категории"""
    category = callback.data.replace("pinterest_cat_", "")
    await state.update_data(category=category)

    await callback.message.edit_text("⏳ Загружаю пины...")

    result = fetch_popular_pins(category=category, count=10)

    await callback.message.delete()

    if result["success"]:
        await send_pins(callback.message, result["items"], category)
    else:
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n{result.get('error', 'Не удалось загрузить')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="pinterest_start")
            ]])
        )

    await callback.answer()


# --- Режим: Трендовые доски ---
@router.callback_query(
    F.data == "pinterest_mode_boards",
    PinterestTrendsForm.waiting_for_mode
)
async def cb_pinterest_boards_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим досок"""
    await callback.message.edit_text("⏳ Загружаю трендовые доски...")

    result = fetch_pinterest_board_trends(count=10)

    await callback.message.delete()

    if result["success"]:
        await send_boards(callback.message, result["items"])
    else:
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n{result.get('error', 'Не удалось загрузить')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="pinterest_start")
            ]])
        )

    await callback.answer()


# --- Режим: Поиск ---
@router.callback_query(
    F.data == "pinterest_mode_search",
    PinterestTrendsForm.waiting_for_mode
)
async def cb_pinterest_search_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим поиска"""
    await state.update_data(mode="search")
    await state.set_state(PinterestTrendsForm.waiting_for_search)

    await callback.message.edit_text(
        "🔍 <b>Поиск в Pinterest</b>\n\n"
        "Введите поисковый запрос:\n\n"
        "Например:\n"
        "• `home decor`\n"
        "• `outfit ideas`\n"
        "• `recipe`",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data="pinterest_cancel")
        ]])
    )
    await callback.answer()


@router.message(PinterestTrendsForm.waiting_for_search)
async def process_pinterest_search(message: types.Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("⚠️ Запрос слишком короткий")
        return

    await state.clear()

    loading = await message.answer("🔍 Ищу...")

    result = search_pinterest(query=query, count=10)

    await loading.delete()

    if result["success"]:
        await send_search_results(message, result["items"], query)
    else:
        await message.answer(
            f"❌ <b>Ошибка поиска</b>\n\n{result.get('error', 'Не удалось найти')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="pinterest_start")
            ]])
        )


# --- Навигация ---
@router.callback_query(F.data == "pinterest_back_to_mode")
async def cb_back_to_mode(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору режима"""
    await state.clear()
    await cb_pinterest_selected(callback, state)


@router.callback_query(F.data == "pinterest_back_to_region")
async def cb_back_to_region(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору региона"""
    data = await state.get_data()

    if data.get("mode") == "keywords":
        await state.set_state(PinterestTrendsForm.waiting_for_region)
        await callback.message.edit_text(
            "🔥 <b>Ключевые слова Pinterest</b>\n\n"
            "Выберите регион:",
            parse_mode="HTML",
            reply_markup=create_region_keyboard()
        )

    await callback.answer()


# --- Обработка текста в неправильном состоянии ---
@router.message(PinterestTrendsForm.waiting_for_region)
async def handle_wrong_input_region(message: types.Message):
    """Если прислали текст вместо выбора региона"""
    await message.answer(
        "⚠️ Пожалуйста, выберите регион из кнопок:",
        reply_markup=create_region_keyboard()
    )


@router.message(PinterestTrendsForm.waiting_for_category)
async def handle_wrong_input_category(message: types.Message):
    """Если прислали текст вместо выбора категории"""
    await message.answer(
        "⚠️ Пожалуйста, выберите категорию из кнопок:",
        reply_markup=create_category_keyboard()
    )