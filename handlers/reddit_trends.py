# handlers/reddit_trends.py
"""
Хендлер для Reddit трендов в MarketPulse с FSM-потоком
"""

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from api.reddit import (
    fetch_subreddit_posts,
    fetch_multiple_subreddits_trending,
    search_reddit,
    SUBREDDITS_BY_CATEGORY,
    TRENDING_SUBREDDITS
)

router = Router()

# === FSM States ===
class RedditTrendsForm(StatesGroup):
    waiting_for_mode = State()       # Выбор режима
    waiting_for_subreddit = State()  # Выбор сабреддита
    waiting_for_sort = State()       # Выбор сортировки
    waiting_for_search = State()    # Ввод поискового запроса


# =============================================================================
# Конфигурация
# =============================================================================
MODES = {
    "🔥 Горячее": "hot",
    "✨ Новое": "new",
    "⭐ Лучшее": "top",
    "🔍 Поиск": "search",
    "📊 Мульти-тренды": "multi",
}

SORT_OPTIONS = {
    "🔥 По горячности": "hot",
    "✨ По новизне": "new",
    "⭐ По голосам": "top",
}

# Быстрые сабреддиты
QUICK_SUBREDDITS = {
    "r/popular": "popular",
    "r/all": "all",
    "r/AskReddit": "AskReddit",
    "r/technology": "technology",
    "r/gaming": "gaming",
    "r/worldnews": "worldnews",
    "r/news": "news",
    "r/science": "science",
}


# =============================================================================
# Клавиатуры
# =============================================================================
def create_mode_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора режима"""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"reddit_mode_{code}")]
        for name, code in MODES.items()
    ]
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="reddit_cancel")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_sort_keyboard(subreddit: str = "") -> InlineKeyboardMarkup:
    """Клавиатура выбора сортировки"""
    prefix = f"reddit_sort_{subreddit}_" if subreddit else "reddit_sort_general_"
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"{prefix}{code}")]
        for name, code in SORT_OPTIONS.items()
    ]
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="reddit_back_to_mode")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_subreddit_keyboard(category: str = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора сабреддита"""
    buttons = []

    if category and category in SUBREDDITS_BY_CATEGORY:
        subs = SUBREDDITS_BY_CATEGORY[category]
    else:
        # Показываем быстрые сабреддиты
        subs = QUICK_SUBREDDITS

    # По 2 в ряду
    items = list(subs.items())
    for i in range(0, len(items), 2):
        row = []
        for name, code in items[i:i+2]:
            display_name = name if name.startswith("r/") else f"r/{name}"
            row.append(InlineKeyboardButton(
                text=display_name,
                callback_data=f"reddit_sub_{code}"
            ))
        buttons.append(row)

    # Категории
    if not category:
        buttons.append([])
        for cat in list(SUBREDDITS_BY_CATEGORY.keys())[:2]:
            buttons[-1].append(InlineKeyboardButton(
                text=cat,
                callback_data=f"reddit_cat_{cat}"
            ))

    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="reddit_back_to_sort"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="reddit_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории"""
    buttons = []
    cats = list(SUBREDDITS_BY_CATEGORY.items())

    for i in range(0, len(cats), 2):
        row = []
        for name, _ in cats[i:i+2]:
            row.append(InlineKeyboardButton(
                text=name,
                callback_data=f"reddit_cat_{name}"
            ))
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="🔙 К быстрым", callback_data="reddit_sub_quick"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="reddit_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =============================================================================
# Формирование сообщений
# =============================================================================
def format_post_message(post: dict, index: int) -> str:
    """Форматирование поста для отображения"""
    emoji = "🔥" if post["score"] >= 10000 else "📈" if post["score"] >= 1000 else "📊"

    title = post["title"]
    if len(title) > 100:
        title = title[:97] + "..."

    text = (
        f"{emoji} <b>{index}. {title}</b>\n"
        f"   👤 u/{post['author']} | r/{post['subreddit']}\n"
        f"   👍 {post['score_formatted']} | 💬 {post['num_comments']} комментариев\n"
    )

    if post["selftext"]:
        text += f"\n   📝 {post['selftext'][:150]}"

    text += f"\n   🔗 <a href='{post['permalink']}'>Открыть</a>"

    return text


async def send_posts(
    message: types.Message,
    posts: list,
    title: str,
    subreddit: str = None
):
    """Отправка постов с форматированием"""
    if not posts:
        await message.answer(
            "❌ Посты не найдены",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="reddit_start")
            ]])
        )
        return

    # Формируем заголовок
    header = f"📊 <b>{title}</b>\n"
    if subreddit:
        header += f"r/{subreddit} | "
    header += f"📈 {len(posts)} постов\n\n"

    # Разбиваем на части
    text = header
    count = 0

    for i, post in enumerate(posts, 1):
        post_text = format_post_message(post, i) + "\n\n"

        # Если добавление поста превысит лимит
        if len(text + post_text) > 4000:
            await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
            text = post_text
        else:
            text += post_text
            count += 1

    # Отправляем остаток
    if text.strip():
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Ещё", callback_data="reddit_start"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
            ]
        ])
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=back_kb)


# =============================================================================
# Хендлеры
# =============================================================================
@router.callback_query(F.data == "plat_reddit")
async def cb_reddit_selected(callback: types.CallbackQuery, state: FSMContext):
    """Начало FSM-потока: выбор режима"""
    await state.clear()
    await state.set_state(RedditTrendsForm.waiting_for_mode)

    await callback.message.edit_text(
        "📊 <b>Reddit Тренды</b>\n\n"
        "Выберите режим:\n\n"
        "🔥 <b>Горячее</b> — популярное сейчас\n"
        "✨ <b>Новое</b> — свежие посты\n"
        "⭐ <b>Лучшее</b> — по голосам\n"
        "🔍 <b>Поиск</b> — найти по запросу\n"
        "📊 <b>Мульти-тренды</b> — с нескольких сабреддитов\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=create_mode_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "reddit_start")
async def cb_reddit_restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск выбора режима"""
    await cb_reddit_selected(callback, state)


@router.callback_query(F.data == "reddit_cancel", StateFilter(RedditTrendsForm))
async def cb_cancel_reddit(callback: types.CallbackQuery, state: FSMContext):
    """Отмена операции"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Операция отменена",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_platforms")
        ]])
    )
    await callback.answer()


# --- Режим: Горячее / Новое / Лучшее ---
@router.callback_query(
    F.data.in_(["reddit_mode_hot", "reddit_mode_new", "reddit_mode_top"]),
    RedditTrendsForm.waiting_for_mode
)
async def cb_reddit_mode_selected(callback: types.CallbackQuery, state: FSMContext):
    """Выбор режима сортировки"""
    mode = callback.data.replace("reddit_mode_", "")
    mode_names = {"hot": "🔥 Горячее", "new": "✨ Новое", "top": "⭐ Лучшее"}

    await state.update_data(mode=mode)
    await state.set_state(RedditTrendsForm.waiting_for_subreddit)

    await callback.message.edit_text(
        f"📊 <b>{mode_names.get(mode, mode)}</b>\n\n"
        "Выберите сабреддит:",
        parse_mode="HTML",
        reply_markup=create_subreddit_keyboard()
    )
    await callback.answer()


# --- Выбор категории ---
@router.callback_query(
    F.data.startswith("reddit_cat_"),
    RedditTrendsForm.waiting_for_subreddit
)
async def cb_reddit_category(callback: types.CallbackQuery, state: FSMContext):
    """Выбор категории сабреддитов"""
    category = callback.data.replace("reddit_cat_", "")

    if category == "quick":
        # Показываем быстрые сабреддиты
        subs = QUICK_SUBREDDITS
    else:
        # Показываем сабреддиты категории
        subs = SUBREDDITS_BY_CATEGORY.get(category, QUICK_SUBREDDITS)

    await state.update_data(category=category, subs=subs)

    await callback.message.edit_text(
        f"📂 Категория: {category}\n\n"
        "Выберите сабреддит:",
        parse_mode="HTML",
        reply_markup=create_subreddit_keyboard(category)
    )
    await callback.answer()


# --- Выбор сабреддита ---
@router.callback_query(
    F.data.startswith("reddit_sub_"),
    RedditTrendsForm.waiting_for_subreddit
)
async def cb_reddit_subreddit(callback: types.CallbackQuery, state: FSMContext):
    """Выбор конкретного сабреддита и загрузка"""
    subreddit = callback.data.replace("reddit_sub_", "")
    data = await state.get_data()
    mode = data.get("mode", "hot")

    await callback.message.edit_text("⏳ Загружаю посты...")
    await callback.answer()

    result = fetch_subreddit_posts(
        subreddit=subreddit,
        sort=mode,
        limit=10
    )

    await callback.message.delete()

    if not result["success"]:
        await callback.message.answer(
            f"❌ <b>Ошибка</b>\n\n{result['error']}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="reddit_start")
            ]])
        )
        return

    mode_names = {"hot": "🔥 Горячее", "new": "✨ Новое", "top": "⭐ Лучшее"}
    title = f"{mode_names.get(mode, mode)} — r/{subreddit}"

    await send_posts(
        message=callback.message,
        posts=result["items"],
        title=title,
        subreddit=subreddit
    )


# --- Режим: Поиск ---
@router.callback_query(
    F.data == "reddit_mode_search",
    RedditTrendsForm.waiting_for_mode
)
async def cb_reddit_search_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим поиска — запрос"""
    await state.update_data(mode="search")
    await state.set_state(RedditTrendsForm.waiting_for_search)

    await callback.message.edit_text(
        "🔍 <b>Поиск в Reddit</b>\n\n"
        "Введите поисковый запрос:\n\n"
        "Например:\n"
        "• `AI news`\n"
        "• `programming tips`\n"
        "• `gaming setup`",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data="reddit_cancel")
        ]])
    )
    await callback.answer()


@router.message(RedditTrendsForm.waiting_for_search)
async def process_reddit_search(message: types.Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = message.text.strip()

    if len(query) < 2:
        await message.answer("⚠️ Запрос слишком короткий")
        return

    await state.clear()

    loading = await message.answer("🔍 Ищу...")

    result = search_reddit(query=query, limit=10)

    await loading.delete()

    if not result["success"]:
        await message.answer(
            f"❌ <b>Ошибка поиска</b>\n\n{result['error']}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="reddit_start")
            ]])
        )
        return

    await send_posts(
        message=message,
        posts=result["items"],
        title=f"🔍 Результаты: {query}"
    )


# --- Режим: Мульти-тренды ---
@router.callback_query(
    F.data == "reddit_mode_multi",
    RedditTrendsForm.waiting_for_mode
)
async def cb_reddit_multi_mode(callback: types.CallbackQuery, state: FSMContext):
    """Режим мульти-трендов"""
    await callback.message.edit_text(
        "📊 <b>Мульти-тренды</b>\n\n"
        "⏳ Загружаю горячие посты с популярных сабреддитов...",
        parse_mode="HTML"
    )
    await callback.answer()

    result = fetch_multiple_subreddits_trending(
        subreddits=TRENDING_SUBREDDITS[:15],
        sort="hot",
        limit_per_sub=2
    )

    if not result["success"]:
        await callback.message.edit_text(
            f"❌ <b>Ошибка</b>\n\n{result['error']}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="reddit_start")
            ]])
        )
        return

    await callback.message.delete()

    # Формируем текст
    text = (
        f"📊 <b>Reddit Мульти-тренды</b>\n"
        f"🔥 Источников: {result['page_info']['subreddits_count']}\n"
        f"📈 Всего постов: {result['page_info']['total_results']}\n\n"
        "═" * 30 + "\n\n"
    )

    # Группируем по сабреддитам
    for subreddit, data in result.get("subreddits_data", {}).items():
        text += f"📂 <b>r/{subreddit}</b>\n"
        for post in data["posts"][:2]:
            title = post["title"]
            if len(title) > 60:
                title = title[:57] + "..."

            emoji = "🔥" if post["score"] >= 5000 else "📈"
            text += f"{emoji} {title}\n"
            text += f"   👍 {post['score_formatted']} | 💬 {post['num_comments']}\n"
        text += "\n"

    # Разбиваем на части
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await callback.message.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)

    # Отправляем с кнопкой повтора
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="reddit_mode_multi"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_platforms")
        ]
    ])
    await callback.message.answer("Выберите действие:", reply_markup=back_kb)


# --- Навигация ---
@router.callback_query(F.data == "reddit_back_to_mode")
async def cb_back_to_mode(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору режима"""
    await state.clear()
    await cb_reddit_selected(callback, state)


@router.callback_query(F.data == "reddit_back_to_sort")
async def cb_back_to_sort(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору сортировки"""
    data = await state.get_data()
    mode = data.get("mode", "hot")
    mode_names = {"hot": "🔥 Горячее", "new": "✨ Новое", "top": "⭐ Лучшее"}

    await state.set_state(RedditTrendsForm.waiting_for_subreddit)

    await callback.message.edit_text(
        f"📊 <b>{mode_names.get(mode, mode)}</b>\n\n"
        "Выберите сабреддит:",
        parse_mode="HTML",
        reply_markup=create_subreddit_keyboard()
    )
    await callback.answer()


# --- Обработка текста в неправильном состоянии ---
@router.message(RedditTrendsForm.waiting_for_subreddit)
async def handle_wrong_input_subreddit(message: types.Message):
    """Если прислали текст вместо выбора"""
    await message.answer(
        "⚠️ Пожалуйста, выберите сабреддит из кнопок:",
        reply_markup=create_subreddit_keyboard()
    )
