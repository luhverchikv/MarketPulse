# api/yandex.py
"""
Модуль для работы с Яндекс.API для получения трендов.
Использует неофициальные методы + Yandex.Wordstat API.

Требования:
    pip install requests beautifulsoup4 lxml

Источники данных:
    - Yandex.Wordstat API (официальный, требует токен)
    - Yandex News (парсинг)
    - Yandex Search (парсинг заголовков)
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional
import re
import json
import time


# =============================================================================
# Константы
# =============================================================================
YANDEX_NEWS_URL = "https://news.yandex.ru"
YANDEX_SEARCH_URL = "https://yandex.ru/search/"
YANDEX_WORDSTAT_URL = "https://api.wordstat.yandex.net"

# Регионы Яндекса
YANDEX_REGIONS = {
    "🇷🇺 Россия": "ru",
    "🇺🇦 Украина": "ua",
    "🇧🇾 Беларусь": "by",
    "🇰🇿 Казахстан": "kz",
    "🇺🇿 Узбекистан": "uz",
    "🇬🇪 Грузия": "ge",
    "🇦🇲 Армения": "am",
    "🇦🇿 Азербайджан": "az",
    "🇰🇬 Кыргызстан": "kg",
    "🇹🇯 Таджикистан": "tj",
    "🇹🇲 Туркменистан": "tm",
    "🇪🇪 Эстония": "ee",
    "🇱🇻 Латвия": "lv",
    "🇱🇹 Литва": "lt",
}

# Категории для парсинга
YANDEX_CATEGORIES = {
    "📰 Все новости": "all",
    "💼 Бизнес": "business",
    "🔬 Технологии": "tech",
    "🎬 Развлечения": "entertainment",
    "⚽ Спорт": "sport",
    "🏥 Здоровье": "health",
    "🔔 Общество": "society",
    "🌍 В мире": "world",
}


# =============================================================================
# Вспомогательные функции
# =============================================================================
def _clean_text(text: str) -> str:
    """Очистка текста от лишних пробелов и спецсимволов"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _get_headers() -> dict:
    """Стандартные заголовки для запросов"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
    }


# =============================================================================
# Функции для получения данных
# =============================================================================
def fetch_yandex_news_trends(
    region: str = "ru",
    category: str = "all",
    max_results: int = 10
) -> dict:
    """
    Получает трендовые новости из Яндекс.Новости.

    🔹 ВХОД:
        region: код региона (ru, ua, by и т.д.)
        category: категория новостей (all, business, tech и т.д.)
        max_results: максимальное количество результатов

    🔹 ВЫХОД:
        dict с полями success, error, items, page_info
    """
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    try:
        # Формируем URL в зависимости от категории
        if category == "all":
            url = f"https://news.yandex.ru/{region}/"
        else:
            url = f"https://news.yandex.ru/{region}/{category}.html"

        response = requests.get(
            url,
            headers=_get_headers(),
            timeout=15
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "lxml")

        # Ищем новости в разных форматах HTML
        news_items = []

        # Формат 1: Классические ссылки новостей
        news_links = soup.select("a.news-tab__link, a.mag-item__link, a.story__link")

        # Формат 2: Список новостей
        if not news_links:
            news_links = soup.select("a[href*='/story/'], a[href*='/article/']")

        # Формат 3: В cards
        if not news_links:
            cards = soup.select(".news-card, .story, .mag-item")
            for card in cards:
                link = card.select_one("a")
                if link:
                    news_links.append(link)

        # Обрабатываем найденные ссылки
        seen_titles = set()
        for link in news_links:
            if len(news_items) >= max_results:
                break

            title = _clean_text(link.get_text())
            href = link.get("href", "")

            # Пропускаем пустые или дубликаты
            if not title or len(title) < 5 or title in seen_titles:
                continue

            # Формируем полный URL
            if href.startswith("/"):
                href = f"https://news.yandex.ru{href}"
            elif not href.startswith("http"):
                href = f"https://news.yandex.ru/{href}"

            # Извлекаем источник
            source = ""
            parent = link.find_parent(".story", ".news-card", ".mag-item")
            if parent:
                source_elem = parent.select_one(".story__source, .news-card__source, .source")
                if source_elem:
                    source = _clean_text(source_elem.get_text())

            news_items.append({
                "title": title,
                "url": href,
                "source": source,
                "category": category,
                "region": region
            })
            seen_titles.add(title)

        # Если не нашли через парсинг, используем API
        if len(news_items) < 3:
            return _fetch_yandex_news_api(region, category, max_results)

        result["success"] = True
        result["items"] = news_items
        result["page_info"] = {
            "total_results": len(news_items),
            "results_per_page": len(news_items)
        }

    except requests.RequestException as e:
        result["error"] = f"Ошибка сети: {str(e)}"
    except Exception as e:
        result["error"] = f"Ошибка парсинга: {type(e).__name__}: {str(e)}"

    return result


def _fetch_yandex_news_api(region: str, category: str, max_results: int) -> dict:
    """Альтернативный метод через API Яндекс.Новостей"""
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    try:
        # Используем внутренний API Яндекса
        api_url = f"https://news.yandex.ru/api/v2/news?geo={region}&count={max_results}"

        if category != "all":
            api_url += f"&category={category}"

        response = requests.get(
            api_url,
            headers=_get_headers(),
            timeout=15
        )
        response.raise_for_status()

        data = response.json()
        items = data.get("items", []) or data.get("news", [])

        news_items = []
        for item in items[:max_results]:
            news_items.append({
                "title": _clean_text(item.get("title", "")),
                "url": item.get("url", ""),
                "source": _clean_text(item.get("source", "")),
                "category": category,
                "region": region,
                "time": item.get("datetime", "")
            })

        result["success"] = True
        result["items"] = news_items
        result["page_info"] = {
            "total_results": len(news_items),
            "results_per_page": len(news_items)
        }

    except (requests.RequestException, json.JSONDecodeError) as e:
        result["error"] = f"API недоступен: {str(e)}"
    except Exception as e:
        result["error"] = f"Ошибка: {type(e).__name__}: {str(e)}"

    return result


def fetch_yandex_search_trends(
    query: str = "",
    region: str = "ru",
    max_results: int = 10
) -> dict:
    """
    Получает популярные поисковые запросы из Яндекс.

    🔹 ВХОД:
        query: поисковый запрос (если пусто — тренды дня)
        region: код региона
        max_results: максимальное количество

    🔹 ВЫХОД:
        dict с полями success, error, items, page_info
    """
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    try:
        # Если есть запрос — получаем похожие
        if query:
            return _fetch_search_suggestions(query, region, max_results)

        # Иначе — получаем тренды дня
        return _fetch_daily_trends(region, max_results)

    except Exception as e:
        result["error"] = f"Ошибка: {type(e).__name__}: {str(e)}"

    return result


def _fetch_search_suggestions(query: str, region: str, max_results: int) -> dict:
    """Получает поисковые подсказки для запроса"""
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    try:
        # Яндекс.Подсказки API
        suggest_url = "https://suggest.yandex.ru/suggest-ya.cgi"
        params = {
            "part": query,
            "lang": region,
            "n": max_results
        }

        response = requests.get(
            suggest_url,
            params=params,
            headers=_get_headers(),
            timeout=10
        )
        response.raise_for_status()

        # Проверяем Content-Type
        content_type = response.headers.get("Content-Type", "")

        if "json" in content_type:
            try:
                data = response.json()
                # Ответ приходит в формате: ["query", ["suggest1", "suggest2", ...]]
                suggestions = data[1] if len(data) > 1 else []

                items = []
                for i, suggest in enumerate(suggestions[:max_results], 1):
                    items.append({
                        "query": _clean_text(suggest),
                        "rank": i,
                        "link": f"https://yandex.ru/search/?text={suggest}&lr={region}",
                        "region": region
                    })

                result["success"] = True
                result["items"] = items
                result["page_info"] = {
                    "total_results": len(items),
                    "results_per_page": len(items)
                }
                return result

            except (json.JSONDecodeError, IndexError) as e:
                # Если JSON не распарсился, используем fallback
                pass

        # Fallback: парсим HTML ответ
        soup = BeautifulSoup(response.content, "lxml")
        items = []

        # Ищем варианты в HTML
        suggestions = soup.select("li.suggest-item, .suggest__item")

        for i, item in enumerate(suggestions[:max_results], 1):
            text = _clean_text(item.get_text())
            if text and len(text) > 1:
                items.append({
                    "query": text,
                    "rank": i,
                    "link": f"https://yandex.ru/search/?text={text}&lr={region}",
                    "region": region
                })

        if items:
            result["success"] = True
            result["items"] = items
            result["page_info"] = {
                "total_results": len(items),
                "results_per_page": len(items)
            }
        else:
            result["error"] = "Подсказки недоступны. Попробуйте позже."

    except requests.RequestException as e:
        result["error"] = f"Ошибка сети: {str(e)}"
    except Exception as e:
        result["error"] = f"Ошибка подсказок: {str(e)}"

    return result


def _fetch_daily_trends(region: str, max_results: int) -> dict:
    """Получает ежедневные тренды из Яндекс"""
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    try:
        # Пытаемся получить тренды из Яндекс.Новости
        trends_url = f"https://yandex.ru/news/"

        response = requests.get(
            trends_url,
            headers=_get_headers(),
            timeout=15
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "lxml")

        # Ищем популярные темы
        trends = []

        # Ищем в разных форматах
        trend_links = soup.select("a.story__link, a.news-tab__link, .trending-item a, .top-news__item a")

        seen = set()
        for link in trend_links:
            if len(trends) >= max_results:
                break

            title = _clean_text(link.get_text())
            href = link.get("href", "")

            if not title or title in seen or len(title) < 5:
                continue

            if href.startswith("/"):
                href = f"https://yandex.ru{href}"

            trends.append({
                "query": title,
                "rank": len(trends) + 1,
                "link": href,
                "region": region
            })
            seen.add(title)

        if not trends:
            result["error"] = "Не удалось получить тренды"
            return result

        result["success"] = True
        result["items"] = trends
        result["page_info"] = {
            "total_results": len(trends),
            "results_per_page": len(trends)
        }

    except Exception as e:
        result["error"] = f"Ошибка: {str(e)}"

    return result


def fetch_yandex_wordstat(
    api_key: str,
    phrase: str,
    region: Optional[str] = None,
    max_results: int = 10
) -> dict:
    """
    Получает статистику запросов из Yandex.Wordstat (официальный API).

    🔹 ВХОД:
        api_key: токен Yandex.Wordstat API
        phrase: поисковая фраза
        region: код региона (опционально)
        max_results: максимальное количество

    🔹 ВЫХОД:
        dict с полями success, error, items, page_info

    ⚠️ Требует:
        pip install requests
        API ключ из Yandex.Direct / Wordstat
    """
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    if not api_key:
        result["error"] = "Не указан API ключ Wordstat"
        return result

    try:
        url = "https://api.wordstat.yandex.net/api/v2/past-dates"
        params = {
            "key": api_key,
            "query": phrase
        }

        if region:
            params["geo"] = region

        response = requests.post(
            url,
            json=params,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 403:
            result["error"] = "Неверный API ключ Wordstat"
            return result

        response.raise_for_status()
        data = response.json()

        # Обрабатываем ответ
        items = []
        for i, day_data in enumerate(data.get("data", [])[:max_results]):
            items.append({
                "phrase": phrase,
                "date": day_data.get("date", ""),
                "shows": day_data.get("shows", 0),
                "region": region or "all"
            })

        result["success"] = True
        result["items"] = items
        result["page_info"] = {
            "total_results": len(items),
            "results_per_page": len(items)
        }

    except requests.RequestException as e:
        result["error"] = f"Ошибка API: {str(e)}"
    except Exception as e:
        result["error"] = f"Ошибка: {type(e).__name__}: {str(e)}"

    return result


# =============================================================================
# Тестовый запуск
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Тестируем Yandex API")
    print("=" * 60)

    # Тест 1: Новостные тренды
    print("\n📰 Тест: Яндекс.Новости тренды (Россия)")
    res = fetch_yandex_news_trends(region="ru", category="tech", max_results=5)

    if res["success"]:
        print(f"✅ Найдено новостей: {res['page_info']['total_results']}")
        for i, item in enumerate(res["items"], 1):
            print(f"{i}. {item['title'][:60]}...")
            print(f"   📎 {item.get('source', 'N/A')}")
    else:
        print(f"❌ Ошибка: {res['error']}")

    # Тест 2: Поисковые подсказки
    print("\n🔍 Тест: Поисковые подсказки")
    res2 = fetch_yandex_search_trends(query="искусственный интеллект", max_results=5)

    if res2["success"]:
        print(f"✅ Найдено подсказок: {res2['page_info']['total_results']}")
        for item in res2["items"]:
            print(f"  → {item['query']}")
    else:
        print(f"❌ Ошибка: {res2['error']}")

    # Тест 3: Ежедневные тренды
    print("\n🔥 Тест: Ежедневные тренды")
    res3 = fetch_yandex_search_trends(max_results=5)

    if res3["success"]:
        print(f"✅ Найдено трендов: {res3['page_info']['total_results']}")
        for item in res3["items"]:
            print(f"  {item['rank']}. {item['query']}")
    else:
        print(f"❌ Ошибка: {res3['error']}")

    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")
    print("=" * 60)
