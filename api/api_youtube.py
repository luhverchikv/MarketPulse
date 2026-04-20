# api/youtube.py
"""
Модуль для работы с YouTube Data API v3

Требования:
    pip install google-api-python-client

Документация API:
    https://developers.google.com/youtube/v3/docs
"""

from typing import Literal, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# =============================================================================
# Константы и типы
# =============================================================================
YouTubeChart = Literal["mostPopular"]  # Пока поддерживаем только trending
YouTubeRegion = Literal[
    "RU", "US", "GB", "DE", "FR", "JP", "KR", "BR", "IN", "CA", "AU"
]
YouTubeCategory = Literal[
    "1", "2", "10", "15", "17", "19", "20", "21", "22", "23", "24", "25", 
    "26", "27", "28", "29", "30", "31", "32", "34", "35", "36", "37", "38", 
    "39", "40", "42", "43", "44"
]
# Популярные категории: 10=Музыка, 20=Игры, 24=Развлечения, 28=Наука и техника


# =============================================================================
# Основная функция
# =============================================================================
def fetch_trending_videos(
    api_key: str,
    region_code: YouTubeRegion = "RU",
    chart: YouTubeChart = "mostPopular",
    max_results: int = 10,
    video_category_id: Optional[YouTubeCategory] = None,
) -> dict:
    """
    Получает список трендовых видео с YouTube.

    🔹 ВХОДНЫЕ ПАРАМЕТРЫ (что требует API):
    ┌─────────────────────┬─────────────┬────────────────────────────┐
    │ Параметр            │ Тип         │ Описание                   │
    ├─────────────────────┼─────────────┼────────────────────────────┤
    │ api_key             │ str         │ Ваш API-ключ Google Cloud  │
    │ region_code         │ str (2 буквы)│ Регион: "RU", "US", etc.  │
    │ chart               │ str         │ Тип тренда: "mostPopular"  │
    │ max_results         │ int (1-50)  │ Сколько видео вернуть      │
    │ video_category_id   │ str or None │ Фильтр по категории (опц.) │
    └─────────────────────┴─────────────┴────────────────────────────┘

    🔹 ВОЗВРАЩАЕМЫЕ ДАННЫЕ (что отдаёт функция):
    {
        "success": bool,           # Успешно ли выполнен запрос
        "error": str | None,       # Сообщение об ошибке (если есть)
        "quota_used": int,         # Сколько квоты потрачено
        "items": [                 # Список видео (макс. max_results)
            {
                "video_id": str,       # ID видео (для ссылки)
                "title": str,          # Заголовок
                "channel": str,        # Название канала
                "channel_id": str,     # ID канала
                "published_at": str,   # ISO 8601 дата публикации
                "view_count": int,     # Просмотры
                "like_count": int,     # Лайки (может быть скрыт)
                "comment_count": int,  # Комментарии
                "thumbnail": str,      # URL превью (medium quality)
                "description": str,    # Краткое описание (первые 200 симв.)
                "tags": list[str],     # Теги видео (если есть)
                "category_id": str,    # ID категории
                "duration": str,       # Длительность в ISO 8601
                "url": str             # Прямая ссылка на видео
            },
            ...
        ],
        "page_info": {
            "total_results": int,    # Всего доступных трендов
            "results_per_page": int  # Сколько вернули в этом запросе
        }
    }

    Пример использования:
        >>> result = fetch_trending_videos("YOUR_API_KEY", region_code="RU", max_results=5)
        >>> if result["success"]:
        ...     for video in result["items"]:
        ...         print(f"{video['title']} — {video['view_count']:,} 👁️")
    """
    
    result = {
        "success": False,
        "error": None,
        "quota_used": 0,
        "items": [],
        "page_info": {}
    }

    try:
        # Инициализация клиента YouTube API
        youtube = build("youtube", "v3", developerKey=api_key)

        # Формируем запрос
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",  # Какие данные запрашиваем
            chart=chart,
            regionCode=region_code,
            maxResults=min(max_results, 50),  # API лимит: 1-50
            videoCategoryId=video_category_id
        )

        # Выполняем запрос
        response = request.execute()
        
        # Считаем потраченную квоту (~3 единицы за запрос + ~1 за каждое видео)
        result["quota_used"] = 3 + len(response.get("items", []))

        # Парсим ответ
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content = item.get("contentDetails", {})
            
            video = {
                "video_id": item["id"],
                "title": snippet.get("title", "Без названия"),
                "channel": snippet.get("channelTitle", "Неизвестный канал"),
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                "description": (snippet.get("description", "")[:200] + "...") if snippet.get("description") else "",
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId", ""),
                "duration": content.get("duration", ""),  # ISO 8601 формат: PT15M33S
                "url": f"https://youtube.com/watch?v={item['id']}"
            }
            result["items"].append(video)

        # Мета-информация
        page_info = response.get("pageInfo", {})
        result["page_info"] = {
            "total_results": page_info.get("totalResults", 0),
            "results_per_page": page_info.get("resultsPerPage", 0)
        }
        
        result["success"] = True

    except HttpError as e:
        # Обработка ошибок API (лимиты, неверный ключ и т.д.)
        error_content = e.content.decode("utf-8") if e.content else str(e)
        result["error"] = f"HTTP {e.resp.status}: {error_content}"
        
    except Exception as e:
        # Обработка прочих ошибок
        result["error"] = f"Unexpected error: {type(e).__name__}: {str(e)}"

    return result


# =============================================================================
# Вспомогательная функция: поиск по ключевым словам (для будущего)
# =============================================================================
def search_trending_topics(
    api_key: str,
    query: str,
    region_code: YouTubeRegion = "RU",
    max_results: int = 5,
    order_by: Literal["relevance", "viewCount", "rating", "date"] = "viewCount"
) -> dict:
    """
    Поиск видео по ключевому слову (для анализа трендов по теме).

    🔹 Вход:
        - query: поисковый запрос (например, "искусственный интеллект")
        - order_by: сортировка результатов ("viewCount" — по просмотрам)
    
    🔹 Выход: та же структура, что у fetch_trending_videos()
    """
    result = {
        "success": False,
        "error": None,
        "quota_used": 0,
        "items": [],
        "page_info": {}
    }

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            regionCode=region_code,
            maxResults=min(max_results, 50),
            order=order_by
        )
        search_response = request.execute()
        
        # Для каждого найденного видео запрашиваем статистику (отдельный вызов API)
        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
        if not video_ids:
            result["success"] = True
            return result
            
        stats_request = youtube.videos().list(
            part="statistics,contentDetails",
            id=",".join(video_ids)
        )
        stats_response = stats_request.execute()
        
        # Объединяем snippet + statistics
        stats_map = {item["id"]: item for item in stats_response.get("items", [])}
        
        for item in search_response.get("items", []):
            snippet = item["snippet"]
            stats = stats_map.get(item["id"]["videoId"], {}).get("statistics", {})
            
            video = {
                "video_id": item["id"]["videoId"],
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                "description": (snippet.get("description", "")[:200] + "...") if snippet.get("description") else "",
                "tags": [],  # search().list не возвращает теги
                "category_id": "",
                "duration": "",
                "url": f"https://youtube.com/watch?v={item['id']['videoId']}"
            }
            result["items"].append(video)
        
        result["quota_used"] = 3 + len(video_ids)  # search + videos.list
        result["page_info"] = search_response.get("pageInfo", {})
        result["success"] = True
        
    except HttpError as e:
        result["error"] = f"HTTP {e.resp.status}: {e.content.decode('utf-8') if e.content else str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {type(e).__name__}: {str(e)}"
    
    return result


# =============================================================================
# Пример запуска (для тестов)
# =============================================================================
if __name__ == "__main__":
    import os
    import json
    
    # Берём ключ из переменной окружения или просим ввести
    API_KEY = os.getenv("YOUTUBE_API_KEY") or input("🔑 Введите YouTube API key: ").strip()
    
    print("🔍 Запрашиваем тренды для RU, категория: Игры (20)...")
    result = fetch_trending_videos(
        api_key=API_KEY,
        region_code="RU",
        video_category_id="20",  # Gaming
        max_results=5
    )
    
    if result["success"]:
        print(f"✅ Запрос успешен | Потрачено квоты: {result['quota_used']}")
        print(f"📊 Всего трендов доступно: {result['page_info']['total_results']}\n")
        
        for i, video in enumerate(result["items"], 1):
            print(f"{i}. {video['title']}")
            print(f"   📺 {video['channel']} | 👁️ {video['view_count']:,}")
            print(f"   🔗 {video['url']}")
            print(f"   🏷 Теги: {', '.join(video['tags'][:3]) if video['tags'] else 'нет'}")
            print()
    else:
        print(f"❌ Ошибка: {result['error']}")
    
    # Сохраняем сырой ответ для анализа структуры
    with open("youtube_sample_response.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("💾 Пример ответа сохранён в youtube_sample_response.json")

