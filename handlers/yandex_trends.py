# handlers/yandex_trends.py
"""
Хендлер для Яндекс.Поиск трендов в MarketPulse с FSM-потоком
"""

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from api.yandex import (
    fetch_yandex_news_trends,
    fetch_yandex_search_trends,
    YANDEX_REGIONS,
    YANDEX_CATEGORIES
)

router = Router()

# === FSM States ===
class YandexTrendsForm(StatesGroup):
    waiting_for_mode = State()      # Выбор режима (новости/поиск)
    waiting_for_region = State()    # Выбор региона
    waiting_for_category = State()  # Выбор категории (для новостей)
    waiting_for_query = State()    # Ввод запроса (для поиска)


# =============================================================================
# Клавиатуры
# =============================================================================
def create_mode_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора режима"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📰 Новостные тренды",
                callback_data="yandex_mode_news"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔍 Поисковые тренды",
                callback_data="yandex_mode_search"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔥 Тренды дня",
                callback_data="yandex_mode_daily"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="yandex_cancel"
            )
        ]
    ])


def create_region_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора региона"""
    keyboard = []
    region_items = list(YANDEX_REGIONS.items())

    # По 2 кнопки в ряду
    for i in range(0, len(region_items), 2):
        row = []
        for name, code in region_items[i:i+2]:
            row.append(InlineKeyboardButton(
                text=name,
                callback_data=f"yandex_region_{code}"
            ))
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="yandex_cancel"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории новостей"""
    keyboard = []
    cat_items = list(YANDEX_CATEGORIES.items())

    for i in range(0, len(cat_items), 2):
        row = []
        for name, code in cat_items[i:i+2]:
            row.append(InlineKeyboardButton(
                text=name,
                callback_data=f"yandex_cat_{code}"
            ))
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад к регионам",
            callback_data="yandex_back_to_region"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="yandex_cancel"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# =============================================================================
# Вспомогательные функции
# =============================================================================
async def fetch_and_send_news_trends(
    message: types.Message,
    region: str,
    category: str
):
    """Загрузка и отправка новостных трендов"""
    loading_msg = await message.answer("⏳ Загружаю новости из Яндекса...")

    result = fetch_yandex_news_trends(
        region=region,
        category=category,
        max_results=10
    )

    await loading_msg.delete()

    if not result["success"]:
        await message.answer(
            f"❌ <b>Ошибка Яндекс.Новости</b>\n\n"
            f"{result['error']}\n\n"
            "Попробуйте выбрать другой регион или категорию.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="yandex_start")
            ]])
        )
        return

    # Формируем сообщение
    region_name = [k for k, v in YANDEX_REGIONS.items() if v == region]
    region_name = region_name[0] if region_name else region

    cat_name = [k for k, v in YANDEX_CATEGORIES.items() if v == category]
    cat_name = cat_name[0] if cat_name else category

    text = (
        f"📰 <b>Яндекс.Новости — {cat_name}</b>\n"
        f"🌍 Регион: {region_name}\n"
        f"📊 Найдено: {result['page_info']['total_results']}\n\n"
    )

    for i, item in enumerate(result["items"], 1):
        emoji = "🔥" if i <= 3 else "📰"
        text += (
            f"{emoji} <b>{i}. {item['title'][:80]}</b>\n"
        )
        if item.get("source"):
            text += f"   📢 {item['source']}\n"
        text += f"   🔗 <a href='{item['url']}'>Читать</a>\n\n"

    # Кнопки навигации
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Другие новости", callback_data="yandex_start"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    # Разбиваем на части
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]

    for idx, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_kb if idx == 0 else None
        )


async def fetch_and_send_search_trends(
    message: types.Message,
    region: str,
    query: str
):
    """Загрузка и отправка поисковых трендов"""
    loading_msg = await message.answer("⏳ Ищу в Яндексе...")

    result = fetch_yandex_search_trends(
        query=query,
        region=region,
        max_results=10
    )

    await loading_msg.delete()

    if not result["success"]:
        await message.answer(
            f"❌ <b>Ошибка поиска</b>\n\n"
            f"{result['error']}\n\n"
            "Попробуйте другой запрос.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="yandex_start")
            ]])
        )
        return

    # Формируем сообщение
    region_name = [k for k, v in YANDEX_REGIONS.items() if v == region]
    region_name = region_name[0] if region_name else region

    text = (
        f"🔍 <b>Яндекс.Поиск — '{query}'</b>\n"
        f"🌍 Регион: {region_name}\n"
        f"📊 Найдено: {result['page_info']['total_results']}\n\n"
    )

    for i, item in enumerate(result["items"], 1):
        emoji = "📈" if i <= 3 else "📊"
        text += (
            f"{emoji} <b>{i}. {item['query'][:60]}</b>\n"
            f"   🔗 <a href='{item['link']}'>Найти</a>\n\n"
        )

    # Кнопки навигации
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Новый поиск", callback_data="yandex_start"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    # Разбиваем на части
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]

    for idx, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_kb if idx == 0 else None
        )


async def fetch_and_send_daily_trends(
    message: types.Message,
    region: str
):
    """Загрузка и отправка ежедневных трендов"""
    loading_msg = await message.answer("⏳ Загружаю тренды дня...")

    result = fetch_yandex_search_trends(
        region=region,
        max_results=10
    )

    await loading_msg.delete()

    if not result["success"]:
        await message.answer(
            f"❌ <b>Ошибка</b>\n\n"
            f"{result['error']}\n\n"
            "Попробуйте позже.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="yandex_start")
            ]])
        )
        return

    # Формируем сообщение
    region_name = [k for k, v in YANDEX_REGIONS.items() if v == region]
    region_name = region_name[0] if region_name else region

    text = (
        f"🔥 <b>Тренды дня — Яндекс</b>\n"
        f"🌍 Регион: {region_name}\n"
        f"📊 Популярные темы: {result['page_info']['total_results']}\n\n"
    )

    for item in result["items"]:
        text += (
            f"#{item['rank']} <b>{item['query'][:60]}</b>\n"
            f"   🔗 <a href='{item['link']}'>Подробнее</a>\n\n"
        )

    # Кнопки навигации
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="yandex_mode_daily"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])

    # Разбиваем на части
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]

    for idx, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_kb if idx == 0 else None
        )


# =============================================================================
# Хендлеры
# =============================================================================
@router.callback_query(F.data == "plat_yandex")
async def cb_yandex_selected(callback: types.CallbackQuery, state: FSMContext):
    """Начало FSM-потока: выбор режима"""
    await state.clear()
    await state.set_state(YandexTrendsForm.waiting_for_mode)

    await callback.message.edit_text(
        "🔍 <b>Яндекс.Поиск</b>\n\n"
        "Выберите режим:\n\n"
        "📰 <b>Новостные тренды</b> — горячие новости\n"
        "🔍 <b>Поисковые тренды</b> — введите запрос\n"
        "🔥 <b>Тренды дня</b> — что ищут сейчас\n\n"
        "Или нажмите ❌ для отмены",
        parse_mode="HTML",
        reply_markup=create_mode_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "yandex_start")
async def cb_yandex_restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск выбора режима"""
    await cb_yandex_selected(callback, state)


@router.callback_query(F.data == "yandex_cancel", StateFilter(YandexTrendsForm))
async def cb_cancel_yandex(callback: types.CallbackQuery, state: FSMContext):
    """Отмена операции"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Операция отменена",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_platforms")
        ]])
    )
    await callback.answer()


# --- Режим: Новости ---
@router.callback_query(F.data == "yandex_mode_news", YandexTrendsForm.waiting_for_mode)
async def cb_yandex_news_mode(callback: types.CallbackQuery, state: FSMContext):
    """Выбор режима 'Новостные тренды'"""
    await state.update_data(mode="news")
    await state.set_state(YandexTrendsForm.waiting_for_region)

    await callback.message.edit_text(
        "📰 <b>Новостные тренды</b>\n\n"
        "Сначала выберите регион:",
        parse_mode="HTML",
        reply_markup=create_region_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "yandex_back_to_region")
async def cb_back_to_region(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору региона"""
    data = await state.get_data()
    await state.set_state(YandexTrendsForm.waiting_for_region)

    mode_text = "📰 Новостные" if data.get("mode") == "news" else "🔍 Поисковые"

    await callback.message.edit_text(
        f"{mode_text} тренды\n\n"
        "Выберите регион:",
        parse_mode="HTML",
        reply_markup=create_region_keyboard()
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("yandex_region_"),
    YandexTrendsForm.waiting_for_region
)
async def cb_yandex_region(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора региона"""
    region = callback.data.replace("yandex_region_", "")
    data = await state.get_data()
    await state.update_data(region=region)

    if data.get("mode") == "news":
        # Переходим к выбору категории
        await state.set_state(YandexTrendsForm.waiting_for_category)
        await callback.message.edit_text(
            "📰 <b>Новостные тренды</b>\n\n"
            "Теперь выберите категорию:",
            parse_mode="HTML",
            reply_markup=create_category_keyboard()
        )
    else:
        # Переходим к вводу запроса
        await state.set_state(YandexTrendsForm.waiting_for_query)
        await callback.message.edit_text(
            "🔍 <b>Поисковые тренды</b>\n\n"
            "Введите поисковый запрос:\n\n"
            "Например:\n"
            "• `нейросети`\n"
            "• `IT вакансии`\n"
            "• `квартиры в Москве`",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="❌ Отмена", callback_data="yandex_cancel")
            ]])
        )

    await callback.answer()


@router.callback_query(
    F.data.startswith("yandex_cat_"),
    YandexTrendsForm.waiting_for_category
)
async def cb_yandex_category(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора категории"""
    category = callback.data.replace("yandex_cat_", "")
    data = await state.get_data()

    await state.clear()

    await callback.message.edit_text("✅ Категория выбрана. Загружаю...")

    await fetch_and_send_news_trends(
        message=callback.message,
        region=data.get("region", "ru"),
        category=category
    )

    await callback.answer()


@router.message(YandexTrendsForm.waiting_for_query)
async def process_yandex_query(message: types.Message, state: FSMContext):
    """Обработка введённого запроса"""
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("⚠️ Запрос слишком короткий. Введите минимум 2 символа.")
        return

    data = await state.get_data()
    await state.clear()

    await fetch_and_send_search_trends(
        message=message,
        region=data.get("region", "ru"),
        query=query
    )


# --- Режим: Поисковые тренды ---
@router.callback_query(F.data == "yandex_mode_search", YandexTrendsForm.waiting_for_mode)
async def cb_yandex_search_mode(callback: types.CallbackQuery, state: FSMContext):
    """Выбор режима 'Поисковые тренды'"""
    await state.update_data(mode="search")
    await state.set_state(YandexTrendsForm.waiting_for_region)

    await callback.message.edit_text(
        "🔍 <b>Поисковые тренды</b>\n\n"
        "Сначала выберите регион:",
        parse_mode="HTML",
        reply_markup=create_region_keyboard()
    )
    await callback.answer()


# --- Режим: Тренды дня ---
@router.callback_query(F.data == "yandex_mode_daily", YandexTrendsForm.waiting_for_mode)
async def cb_yandex_daily_mode(callback: types.CallbackQuery, state: FSMContext):
    """Выбор режима 'Тренды дня'"""
    await state.update_data(mode="daily")
    await state.set_state(YandexTrendsForm.waiting_for_region)

    await callback.message.edit_text(
        "🔥 <b>Тренды дня</b>\n\n"
        "Выберите регион:",
        parse_mode="HTML",
        reply_markup=create_region_keyboard()
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("yandex_region_"),
    YandexTrendsForm.waiting_for_region
)
async def cb_yandex_region_daily(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора региона для трендов дня"""
    region = callback.data.replace("yandex_region_", "")
    data = await state.get_data()

    await state.clear()

    await callback.message.edit_text("✅ Регион выбран. Загружаю тренды...")

    await fetch_and_send_daily_trends(
        message=callback.message,
        region=region
    )

    await callback.answer()


# --- Обработка текстовых сообщений в неправильном состоянии ---
@router.message(YandexTrendsForm.waiting_for_region)
async def handle_wrong_input_region(message: types.Message):
    """Если пользователь прислал текст вместо выбора региона"""
    await message.answer(
        "⚠️ Пожалуйста, выберите регион из кнопок ниже:",
        reply_markup=create_region_keyboard()
    )


@router.message(YandexTrendsForm.waiting_for_category)
async def handle_wrong_input_category(message: types.Message):
    """Если пользователь прислал текст вместо выбора категории"""
    await message.answer(
        "⚠️ Пожалуйста, выберите категорию из кнопок ниже:",
        reply_markup=create_category_keyboard()
    )
