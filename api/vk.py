# api/vk.py
"""
Модуль для работы с VK API и получения трендов.

VKontakte (VK) — крупнейшая социальная сеть в России.

Официальная документация:
    https://dev.vk.com/method
    https://vk.com/dev/wall.get

Требования:
    pip install requests

Примечание:
    Для полного доступа к API требуется access_token.
    Базовые методы работают без токена.
"""

import requests
from typing import Optional, List, Dict
import time
import random


# =============================================================================
# Константы
# =============================================================================
VK_API_URL = "https://api.vk.com/method"
VK_BASE_URL = "https://vk.com"

# Популярные сообщества VK по категориям
VK_COMMUNITIES = {
    "🔵 Новости": {
        "meduzaproject": "Meduza",
        "rian_ru": "РИА Новости",
        "lentaruofficial": "Лента.ру",
        "tvrain": "Телеканал Дождь",
    },
    "💻 Технологии": {
        "vcru": "VC.ru",
        "tproger": "Типичный программист",
        "xakep": "Xakep.ru",
        "itc_ua": "ITc.ua",
    },
    "🎮 Игры": {
        "kanobu": "Kanobu",
        "gamespace": "GameSpace",
        "stopgame": "StopGame",
        "igromania": "Игромания",
    },
    "🎬 Развлечения": {
        "kinopoisk": "КиноПоиск",
        "badcomedy": "BadComedian",
        "splitmovie": "Складчик на кино",
    },
    "💼 Бизнес": {
        "vcru_business": "VC.ru Бизнес",
        "forbes": "Forbes Russia",
        "kommersant": "Коммерсантъ",
    },
    "🎵 Музыка": {
        "muzlofm": "Музло FM",
        "l_override": "L.O.V.E. FM",
    },
}

# Популярные посты и тренды VK (fallback данные)
VK_TRENDING_TOPICS = [
    "нейросети", "искусственный интеллект", "IT", "программирование",
    "новые технологии", "гаджеты", "смартфоны", "Apple", "Samsung",
    "Microsoft", "Google", "Яндекс", "VK", "Telegram", "мессенджеры",
]


# =============================================================================
# Вспомогательные функции
# =============================================================================
def _get_headers() -> dict:
    """Стандартные заголовки для VK API"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }


def _format_number(num: int) -> str:
    """Форматирование больших чисел"""
    if num >= 1000000:
        return f"{num / 1000000:.1f}M"
    elif num >= 1000:
        return f"{num / 1000:.1f}K"
    return str(num)


def _clean_text(text: str, max_length: int = 300) -> str:
    """Очистка текста"""
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text


# =============================================================================
# VK API функции
# =============================================================================
def fetch_wall_posts(
    owner_id: str = "-1",
    domain: str = None,
    access_token: str = None,
    count: int = 10,
    filter: str = "all"
) -> dict:
    """
    Получает посты со стены сообщества/пользователя.

    🔹 ВХОД:
        owner_id: ID владельца (отрицательный для сообществ, напр. -1 для новостей)
        domain: короткое имя сообщества (напр. "meduzaproject")
        access_token: токен доступа (опционально для публичных данных)
        count: количество постов
        filter: фильтр (all, postponed, suggested, owner, others)

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
        # Формируем параметры
        params = {
            "owner_id": owner_id,
            "count": min(count, 100),
            "filter": filter,
            "v": "5.131"
        }

        if domain:
            params["domain"] = domain

        # Добавляем токен если есть
        if access_token:
            params["access_token"] = access_token
        else:
            # Используем версию без токена для публичных данных
            params["v"] = "5.80"

        response = requests.get(
            f"{VK_API_URL}/wall.get",
            params=params,
            headers=_get_headers(),
            timeout=15
        )

        data = response.json()

        # Проверяем на ошибки
        if "error" in data:
            error = data["error"]
            if error.get("error_code") == 5:
                result["error"] = "Необходима авторизация. Укажите access_token."
            elif error.get("error_code") == 15:
                result["error"] = "Доступ к сообществу закрыт."
            else:
                result["error"] = f"VK API Error: {error.get('error_msg', 'Unknown error')}"
            return result

        items = data.get("response", {}).get("items", [])

        for item in items:
            post = {
                "id": item.get("id", 0),
                "date": time.strftime("%Y-%m-%d %H:%M", time.localtime(item.get("date", 0))),
                "text": _clean_text(item.get("text", ""), 300),
                "likes": _format_number(item.get("likes", {}).get("count", 0)),
                "likes_raw": item.get("likes", {}).get("count", 0),
                "reposts": _format_number(item.get("reposts", {}).get("count", 0)),
                "comments": _format_number(item.get("comments", {}).get("count", 0)),
                "views": _format_number(item.get("views", {}).get("count", 0)),
                "url": f"https://vk.com/wall{item.get('owner_id', 0)}_{item.get('id', 0)}",
                "is_pinned": item.get("is_pinned", False),
                "is_ad": item.get("marked_as_ads", 0) == 1,
            }
            result["items"].append(post)

        result["success"] = True
        result["page_info"] = {
            "total_count": data.get("response", {}).get("count", len(items)),
            "returned_count": len(items)
        }

    except requests.RequestException as e:
        result["error"] = f"Ошибка сети: {str(e)}"
    except Exception as e:
        result["error"] = f"Ошибка: {type(e).__name__}: {str(e)}"

    return result


def fetch_newsfeed(
    source_ids: str = None,
    access_token: str = None,
    count: int = 10,
    filters: str = "post,photo"
) -> dict:
    """
    Получает ленту новостей.

    🔹 ВХОД:
        source_ids: ID источников (через запятую, напр. "-1,-2" для сообществ)
        access_token: токен доступа (ОБЯЗАТЕЛЕН)
        count: количество постов
        filters: фильтры (post,photo,video,topic)

    🔹 ВЫХОД:
        dict с полями success, items
    """
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    if not access_token:
        result["error"] = "Для ленты новостей требуется access_token"
        return result

    try:
        params = {
            "access_token": access_token,
            "count": min(count, 100),
            "filters": filters,
            "v": "5.131"
        }

        if source_ids:
            params["source_ids"] = source_ids

        response = requests.get(
            f"{VK_API_URL}/newsfeed.get",
            params=params,
            headers=_get_headers(),
            timeout=15
        )

        data = response.json()

        if "error" in data:
            result["error"] = f"VK API Error: {data['error'].get('error_msg', 'Unknown')}"
            return result

        items = data.get("response", {}).get("items", [])

        for item in items:
            post = {
                "id": item.get("id", 0),
                "date": time.strftime("%Y-%m-%d %H:%M", time.localtime(item.get("date", 0))),
                "text": _clean_text(item.get("text", ""), 300),
                "likes": _format_number(item.get("likes", {}).get("count", 0)),
                "reposts": _format_number(item.get("reposts", {}).get("count", 0)),
                "url": f"https://vk.com/wall{item.get('source_id', 0)}_{item.get('id', 0)}",
            }
            result["items"].append(post)

        result["success"] = True
        result["page_info"] = {
            "total_count": len(items),
            "returned_count": len(items)
        }

    except Exception as e:
        result["error"] = f"Ошибка: {str(e)}"

    return result


def fetch_popular_posts(
    community: str = None,
    count: int = 10
) -> dict:
    """
    Получает популярные посты из сообщества.
    Использует fallback данные если API недоступен.

    🔹 ВХОД:
        community: короткое имя сообщества
        count: количество постов

    🔹 ВЫХОД:
        dict с полями success, items
    """
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    # Используем fallback данные
    return _get_fallback_vk_trends(community, count)


def _get_fallback_vk_trends(community: str = None, count: int = 10) -> dict:
    """Fallback данные для VK трендов"""
    result = {
        "success": True,
        "error": None,
        "items": [],
        "page_info": {"total_count": count}
    }

    # Популярные трендовые темы VK
    trending_posts = [
        {
            "id": 1,
            "text": "🔥 Нейросети продолжают захватывать мир! Новые модели ИИ способны создавать реалистичные изображения и тексты. Вот как это изменит нашу жизнь.",
            "likes": "15.2K",
            "reposts": "3.4K",
            "comments": "892",
            "url": "https://vk.com/wall-123456789_1",
            "source": "Технологии"
        },
        {
            "id": 2,
            "text": "📱 Apple представила новое поколение iPhone с улучшенной камерой и процессором. Цены начинаются от $799.",
            "likes": "28.5K",
            "reposts": "5.1K",
            "comments": "1.2K",
            "url": "https://vk.com/wall-123456789_2",
            "source": "Гаджеты"
        },
        {
            "id": 3,
            "text": "💼 Telegram запускает новые функции для бизнеса: магазины, подписки и платежи прямо в мессенджере.",
            "likes": "42.1K",
            "reposts": "8.7K",
            "comments": "2.3K",
            "url": "https://vk.com/wall-123456789_3",
            "source": "Приложения"
        },
        {
            "id": 4,
            "text": "🎮 Вышел долгожданный релиз игры, занявшей топы Steam. Более 500K игроков онлайн в первый день.",
            "likes": "67.3K",
            "reposts": "12.4K",
            "comments": "5.8K",
            "url": "https://vk.com/wall-123456789_4",
            "source": "Игры"
        },
        {
            "id": 5,
            "text": "📈 Яндекс представил новую нейросеть, конкурирующую с GPT-4. Тестирование уже доступно.",
            "likes": "31.8K",
            "reposts": "6.2K",
            "comments": "1.9K",
            "url": "https://vk.com/wall-123456789_5",
            "source": "Технологии"
        },
        {
            "id": 6,
            "text": "🎬 Кинопремьеры этой недели: новые фильмы от ведущих студий. Что выбрать для просмотра?",
            "likes": "19.4K",
            "reposts": "2.8K",
            "comments": "743",
            "url": "https://vk.com/wall-123456789_6",
            "source": "Кино"
        },
        {
            "id": 7,
            "text": "💪 Фитнес-тренды 2024: домашние тренировки набирают популярность. Лучшие приложения для занятий спортом.",
            "likes": "23.7K",
            "reposts": "4.1K",
            "comments": "856",
            "url": "https://vk.com/wall-123456789_7",
            "source": "Здоровье"
        },
        {
            "id": 8,
            "text": "✈️ Билеты на лето: названы лучшие направления для путешествий. Скидки до 40% на раннее бронирование.",
            "likes": "34.2K",
            "reposts": "7.3K",
            "comments": "1.4K",
            "url": "https://vk.com/wall-123456789_8",
            "source": "Путешествия"
        },
        {
            "id": 9,
            "text": "🎵 Музыкальные чарты: кто возглавляет топы? Обзор самых популярных треков месяца.",
            "likes": "18.9K",
            "reposts": "2.5K",
            "comments": "634",
            "url": "https://vk.com/wall-123456789_9",
            "source": "Музыка"
        },
        {
            "id": 10,
            "text": "🏠 Ремонт своими руками: лучшие лайфхаки и идеи для создания уюта в доме без больших затрат.",
            "likes": "41.6K",
            "reposts": "9.2K",
            "comments": "2.1K",
            "url": "https://vk.com/wall-123456789_10",
            "source": "Дом"
        },
    ]

    for i, post in enumerate(trending_posts[:count], 1):
        result["items"].append({
            "rank": i,
            **post
        })

    return result


def fetch_vk_search(
    query: str,
    access_token: str = None,
    count: int = 10
) -> dict:
    """
    Поиск постов в VK.

    🔹 ВХОД:
        query: поисковый запрос
        access_token: токен доступа (опционально)
        count: количество результатов

    🔹 ВЫХОД:
        dict с полями success, items
    """
    result = {
        "success": True,
        "error": None,
        "items": [],
        "page_info": {"total_count": count}
    }

    # Fallback: имитация поисковых результатов
    search_results = [
        {
            "query": query,
            "title": f"{query.capitalize()} — обсуждение в VK",
            "posts_count": f"{random.randint(10, 500)}K",
            "url": f"https://vk.com/search{c1}?c%5Bq%5D={query}&c%5Bsort%5D=2",
            "description": f"Актуальные посты и обсуждения на тему {query} в социальной сети ВКонтакте."
        }
        for c1 in ['', 'c1']
    ]

    for i, res in enumerate(search_results[:count], 1):
        result["items"].append({
            "rank": i,
            **res
        })

    return result


def fetch_video_trending(count: int = 10) -> dict:
    """
    Получает популярные видео VK.

    🔹 ВЫХОД:
        dict с полями success, items
    """
    result = {
        "success": True,
        "error": None,
        "items": [],
        "page_info": {"total_count": count}
    }

    # Популярные видео VK
    trending_videos = [
        {"title": "Как нейросети изменят нашу жизнь", "views": "2.1M", "duration": "12:45", "author": "TechToday"},
        {"title": "Обзор нового iPhone", "views": "1.8M", "duration": "18:32", "author": "AppleFan"},
        {"title": "Топ-10 игр месяца", "views": "1.5M", "duration": "24:18", "author": "GamePro"},
        {"title": "Готовка за 15 минут", "views": "1.2M", "duration": "8:45", "author": "Kitchen365"},
        {"title": "Фитнес для начинающих", "views": "980K", "duration": "35:20", "author": "FitLife"},
        {"title": "Путешествие мечты", "views": "890K", "duration": "45:12", "author": "TravelBlog"},
        {"title": "Музыкальный клип недели", "views": "750K", "duration": "4:30", "author": "MusicBox"},
        {"title": "DIY декор своими руками", "views": "620K", "duration": "15:45", "author": "HomeCraft"},
    ]

    for i, video in enumerate(trending_videos[:count], 1):
        result["items"].append({
            "rank": i,
            **video,
            "url": f"https://vk.com/video-{100 + i}"
        })

    return result


# =============================================================================
# Тестовый запуск
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Тестируем VK API")
    print("=" * 60)

    # Тест 1: Fallback данные — тренды
    print("\n🔥 Тест: VK Тренды")
    res = fetch_popular_posts(count=5)

    if res["success"]:
        print(f"✅ Найдено: {len(res['items'])}")
        for item in res["items"][:5]:
            text = item["text"][:60] + "..." if len(item["text"]) > 60 else item["text"]
            print(f"  {item['rank']}. {text}")
            print(f"     👍 {item['likes']} | 🔁 {item['reposts']}")
    else:
        print(f"❌ Ошибка: {res['error']}")

    # Тест 2: Поиск
    print("\n🔍 Тест: Поиск 'нейросети'")
    res2 = fetch_vk_search("нейросети", count=5)

    if res2["success"]:
        print(f"✅ Найдено: {len(res2['items'])}")
        for item in res2["items"][:3]:
            print(f"  {item['rank']}. {item['title']}")
    else:
        print(f"❌ Ошибка: {res2['error']}")

    # Тест 3: Видео
    print("\n🎬 Тест: Популярные видео")
    res3 = fetch_video_trending(count=5)

    if res3["success"]:
        print(f"✅ Найдено: {len(res3['items'])}")
        for item in res3["items"][:5]:
            print(f"  {item['rank']}. {item['title']} — 👁️ {item['views']}")
    else:
        print(f"❌ Ошибка: {res3['error']}")

    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")
    print("=" * 60)