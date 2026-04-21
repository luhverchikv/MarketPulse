# api/reddit.py
"""
Модуль для работы с Reddit API.
Использует публичный JSON API Reddit — не требует ключей!

Документация:
    https://www.reddit.com/dev/api
    https://www.reddit.com/r/{subreddit}/hot.json
"""

import requests
from typing import Optional
import time


# =============================================================================
# Константы
# =============================================================================
REDDIT_API_BASE = "https://www.reddit.com"
REDDIT_OAUTH_BASE = "https://oauth.reddit.com"

# Популярные сабреддиты по категориям
SUBREDDITS_BY_CATEGORY = {
    "📰 Новости": {
        "worldnews": "Мировые новости",
        "news": "Новости",
        "technology": "Технологии",
    },
    "💻 Технологии": {
        "technology": "Технологии",
        "programming": "Программирование",
        "人工智能": "AI / ML (Китайский)",
    },
    "🎮 Игры": {
        "gaming": "Игры",
        "pcgaming": "PC Gaming",
        "PS5": "PlayStation",
        "xbox": "Xbox",
    },
    "💼 Бизнес": {
        "business": "Бизнес",
        "entrepreneur": "Предпринимательство",
        "investing": "Инвестиции",
    },
    "🎬 Развлечения": {
        "movies": "Фильмы",
        "television": "ТВ",
        "music": "Музыка",
    },
    "🔬 Наука": {
        "science": "Наука",
        "space": "Космос",
        "technology": "Технологии",
    },
}

# Популярные сабреддиты для трендов
TRENDING_SUBREDDITS = [
    "popular",
    "all",
    "AskReddit",
    "worldnews",
    "technology",
    "gaming",
    "news",
    "Music",
    "movies",
    "science",
]


# =============================================================================
# Вспомогательные функции
# =============================================================================
def _get_headers(user_agent: str = None) -> dict:
    """Стандартные заголовки для Reddit API"""
    if user_agent is None:
        # Reddit требует уникальный User-Agent
        import random
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        user_agent = random.choice(agents)

    return {
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _format_score(score: int) -> str:
    """Форматирование числа голосов"""
    if score >= 1000000:
        return f"{score / 1000000:.1f}M"
    elif score >= 1000:
        return f"{score / 1000:.1f}K"
    return str(score)


def _clean_text(text: str, max_length: int = 300) -> str:
    """Очистка и обрезка текста"""
    if not text:
        return ""
    # Удаляем лишние пробелы
    text = " ".join(text.split())
    # Удаляем переносы строк
    text = text.replace("\n", " ")
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text


def _parse_post(post_data: dict) -> dict:
    """Парсинг данных поста из Reddit API"""
    data = post_data.get("data", {})

    # Определяем тип медиа
    post_hint = data.get("post_hint", "")
    is_video = data.get("is_video", False)
    thumbnail = data.get("thumbnail", "")

    # Формируем URL
    permalink = data.get("permalink", "")
    url = data.get("url", "")

    # Если это reddit link, используем permalink
    if "reddit.com/r/" in url and "/comments/" not in url:
        post_url = f"https://reddit.com{permalink}"
    else:
        post_url = url if url.startswith("http") else f"https://reddit.com{permalink}"

    return {
        "id": data.get("id", ""),
        "title": _clean_text(data.get("title", "Без названия"), 200),
        "author": data.get("author", "[deleted]"),
        "subreddit": data.get("subreddit", ""),
        "subreddit_prefixed": data.get("subreddit_name_prefixed", ""),
        "score": data.get("score", 0),
        "score_formatted": _format_score(data.get("score", 0)),
        "ups": data.get("ups", 0),
        "downs": data.get("downs", 0),
        "num_comments": data.get("num_comments", 0),
        "created_utc": data.get("created_utc", 0),
        "created_date": time.strftime(
            "%Y-%m-%d %H:%M",
            time.gmtime(data.get("created_utc", 0))
        ) if data.get("created_utc") else "",
        "domain": data.get("domain", ""),
        "url": post_url,
        "permalink": f"https://reddit.com{permalink}" if permalink else "",
        "thumbnail": thumbnail if thumbnail.startswith("http") else "",
        "is_video": is_video,
        "is_self": data.get("is_self", False),
        "selftext": _clean_text(data.get("selftext", ""), 500),
        "link_flair_text": data.get("link_flair_text", ""),
        "over_18": data.get("over_18", False),
        "spoiler": data.get("spoiler", False),
        "pinned": data.get("pinned", False),
        "distinguished": data.get("distinguished", None),
    }


# =============================================================================
# Основные функции API
# =============================================================================
def fetch_subreddit_posts(
    subreddit: str = "popular",
    sort: str = "hot",
    limit: int = 10,
    after: Optional[str] = None,
) -> dict:
    """
    Получает посты из сабреддита.

    🔹 ВХОД:
        subreddit: название сабреддита (без r/)
        sort: сортировка (hot, new, top, rising, controversial)
        limit: количество постов (макс 100)
        after: cursor для пагинации (опционально)

    🔹 ВЫХОД:
        dict с полями success, error, items, page_info
    """
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    if limit > 100:
        limit = 100

    try:
        # Формируем URL
        url = f"{REDDIT_API_BASE}/r/{subreddit}/{sort}.json"
        params = {
            "limit": limit,
            "raw_json": 1,
        }
        if after:
            params["after"] = after

        response = requests.get(
            url,
            params=params,
            headers=_get_headers(),
            timeout=15,
            allow_redirects=True
        )

        if response.status_code == 404:
            result["error"] = f"Сабреддит r/{subreddit} не найден"
            return result

        if response.status_code == 429:
            result["error"] = "Слишком много запросов. Reddit ограничивает частые обращения. Попробуйте через несколько минут."
            return result

        if response.status_code == 403:
            result["error"] = "Доступ к Reddit ограничен в текущей среде. API будет работать на вашем сервере."
            return result

        if response.status_code == 502 or response.status_code == 503:
            result["error"] = "Reddit временно недоступен. Попробуйте позже."
            return result

        response.raise_for_status()
        data = response.json()

        # Парсим данные
        children = data.get("data", {}).get("children", [])

        for post in children:
            item = _parse_post(post)
            result["items"].append(item)

        # Информация для пагинации
        result["page_info"] = {
            "total_results": len(result["items"]),
            "results_per_page": limit,
            "after": data.get("data", {}).get("after"),
            "before": data.get("data", {}).get("before"),
        }

        result["success"] = True

    except requests.RequestException as e:
        result["error"] = f"Ошибка сети: {str(e)}"
    except Exception as e:
        result["error"] = f"Ошибка парсинга: {type(e).__name__}: {str(e)}"

    return result


def fetch_multiple_subreddits_trending(
    subreddits: list = None,
    sort: str = "hot",
    limit_per_sub: int = 3
) -> dict:
    """
    Получает топ посты из нескольких сабреддитов.

    🔹 ВХОД:
        subreddits: список сабреддитов (по умолчанию TRENDING_SUBREDDITS)
        sort: сортировка
        limit_per_sub: лимит на каждый сабреддит

    🔹 ВЫХОД:
        dict с полями success, error, items (сгруппированные по сабреддиту)
    """
    result = {
        "success": False,
        "error": None,
        "items": [],
        "subreddits_data": {},
        "page_info": {}
    }

    if subreddits is None:
        subreddits = TRENDING_SUBREDDITS[:10]  # Ограничиваем до 10

    for subreddit in subreddits:
        try:
            sub_result = fetch_subreddit_posts(
                subreddit=subreddit,
                sort=sort,
                limit=limit_per_sub
            )

            if sub_result["success"] and sub_result["items"]:
                result["subreddits_data"][subreddit] = {
                    "count": len(sub_result["items"]),
                    "posts": sub_result["items"]
                }
                result["items"].extend(sub_result["items"])

        except Exception:
            continue

        # Rate limiting — пауза между запросами
        time.sleep(0.5)

    if not result["items"]:
        result["error"] = "Не удалось получить данные"
        return result

    # Сортируем по score
    result["items"].sort(key=lambda x: x["score"], reverse=True)

    result["page_info"] = {
        "total_results": len(result["items"]),
        "subreddits_count": len(result["subreddits_data"]),
    }

    result["success"] = True
    return result


def fetch_subreddit_info(subreddit: str) -> dict:
    """
    Получает информацию о сабреддите.

    🔹 ВЫХОД:
        dict с данными о сабреддите
    """
    result = {
        "success": False,
        "error": None,
        "data": {}
    }

    try:
        url = f"{REDDIT_API_BASE}/r/{subreddit}/about.json"
        response = requests.get(
            url,
            headers=_get_headers(),
            timeout=10
        )

        if response.status_code == 404:
            result["error"] = f"Сабреддит r/{subreddit} не найден"
            return result

        response.raise_for_status()
        data = response.json()
        about = data.get("data", {})

        result["data"] = {
            "name": about.get("display_name", ""),
            "title": about.get("title", ""),
            "description": about.get("description", ""),
            "subscribers": about.get("subscribers", 0),
            "active_users": about.get("active_user_count", 0),
            "public_description": about.get("public_description", ""),
            "icon_img": about.get("icon_img", ""),
            "banner_img": about.get("banner_img", ""),
            "over_18": about.get("over_18", False),
            "lang": about.get("lang", ""),
        }

        result["success"] = True

    except Exception as e:
        result["error"] = f"Ошибка: {str(e)}"

    return result


def search_reddit(
    query: str,
    sort: str = "relevance",
    time_filter: str = "week",
    limit: int = 10
) -> dict:
    """
    Поиск по Reddit.

    🔹 ВХОД:
        query: поисковый запрос
        sort: сортировка (relevance, hot, top, new, comments)
        time_filter: период (hour, day, week, month, year, all)
        limit: количество результатов

    🔹 ВЫХОД:
        dict с полями success, error, items
    """
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    try:
        url = f"{REDDIT_API_BASE}/search.json"
        params = {
            "q": query,
            "sort": sort,
            "t": time_filter,
            "limit": min(limit, 100),
            "restrict_sr": False,
            "raw_json": 1,
        }

        response = requests.get(
            url,
            params=params,
            headers=_get_headers(),
            timeout=15
        )

        if response.status_code == 429:
            result["error"] = "Слишком много запросов"
            return result

        response.raise_for_status()
        data = response.json()

        children = data.get("data", {}).get("children", [])

        for post in children:
            item = _parse_post(post)
            item["relevance"] = post.get("data", {}).get("relevance", 0)
            result["items"].append(item)

        result["page_info"] = {
            "total_results": len(result["items"]),
            "results_per_page": len(result["items"]),
        }

        result["success"] = True

    except Exception as e:
        result["error"] = f"Ошибка: {str(e)}"

    return result


# =============================================================================
# Тестовый запуск
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Тестируем Reddit API")
    print("=" * 60)

    # Тест 1: Популярные посты
    print("\n📊 Тест: r/popular — Hot")
    res = fetch_subreddit_posts("popular", sort="hot", limit=3)

    if res["success"]:
        print(f"✅ Найдено: {res['page_info']['total_results']}")
        for post in res["items"]:
            print(f"\n📌 {post['title'][:60]}...")
            print(f"   👍 {post['score_formatted']} | 💬 {post['num_comments']} | r/{post['subreddit']}")
    else:
        print(f"❌ Ошибка: {res['error']}")

    # Тест 2: Сабреддит по категориям
    print("\n\n🎮 Тест: r/gaming — New")
    res2 = fetch_subreddit_posts("gaming", sort="new", limit=3)

    if res2["success"]:
        print(f"✅ Найдено: {res2['page_info']['total_results']}")
        for post in res2["items"]:
            print(f"\n📌 {post['title'][:60]}...")
            print(f"   👍 {post['score_formatted']} | 💬 {post['num_comments']}")
    else:
        print(f"❌ Ошибка: {res2['error']}")

    # Тест 3: Информация о сабреддите
    print("\n\nℹ️ Тест: Информация о r/technology")
    info = fetch_subreddit_info("technology")

    if info["success"]:
        print(f"✅ Название: {info['data']['title']}")
        print(f"   👥 Подписчики: {info['data']['subscribers']:,}")
        print(f"   🟢 Активных: {info['data']['active_users']:,}")
    else:
        print(f"❌ Ошибка: {info['error']}")

    # Тест 4: Поиск
    print("\n\n🔍 Тест: Поиск 'AI news'")
    search = search_reddit("AI news", limit=3)

    if search["success"]:
        print(f"✅ Найдено: {search['page_info']['total_results']}")
        for post in search["items"][:3]:
            print(f"\n📌 {post['title'][:60]}...")
    else:
        print(f"❌ Ошибка: {search['error']}")

    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")
    print("=" * 60)
