# api/google_trends.py
"""
Модуль для работы с Google Trends через pytrends.
Возвращает данные в том же формате, что и YouTube API.
"""

from pytrends.request import TrendReq
from pytrends.exceptions import TooManyRequestsError
import pandas as pd
import time
from typing import Optional


def fetch_google_trends(
    region: str = "RU",
    topic: str = "AI",
    period: str = "7d",
    max_results: int = 10
) -> dict:
    """
    Получает связанные запросы из Google Trends.
    
    🔹 ВХОД:
        region: код страны (RU, US, BY и т.д.)
        topic: ключевое слово/тема
        period: период (1d, 7d, 14d, 30d)
        max_results: сколько топ-запросов вернуть
        
    🔹 ВЫХОД:
        dict с полями success, error, items, page_info
    """
    result = {
        "success": False,
        "error": None,
        "items": [],
        "page_info": {}
    }

    # Маппинг периода в формат pytrends
    period_map = {
        "1d": "now 1-d",
        "7d": "now 7-d",
        "14d": "now 14-d",
        "30d": "now 30-d"
    }
    timeframe = period_map.get(period, "now 7-d")

    try:
        # Инициализация клиента (hl=ru для русского интерфейса, tz=360 для MSK)
        pytrends = TrendReq(hl="ru", tz=360, timeout=10)
        
        # Формируем запрос
        pytrends.build_payload(
            kw_list=[topic],
            cat=0,
            timeframe=timeframe,
            geo=region,
            gprop=""
        )

        # Получаем связанные запросы
        related = pytrends.related_queries()
        top_queries = related[topic].get("top", pd.DataFrame())

        if top_queries.empty:
            result["error"] = "Нет данных по этому запросу в выбранном регионе"
            return result

        # Форматируем результаты
        for _, row in top_queries.iterrows():
            if len(result["items"]) >= max_results:
                break
                
            result["items"].append({
                "query": row["query"],
                "volume": int(row["value"]),
                "link": f"https://trends.google.com/trends/explore?q={row['query']}&geo={region}",
                "growth": None  # pytrends не отдает % роста для top queries
            })

        result["success"] = True
        result["page_info"] = {
            "total_results": len(top_queries),
            "results_per_page": len(result["items"])
        }

    except TooManyRequestsError:
        result["error"] = "🚫 Google Trends: слишком много запросов. Подождите 5-10 минут."
    except Exception as e:
        result["error"] = f"⚠️ Ошибка: {type(e).__name__}: {str(e)}"

    return result


# 🔧 Тестовый запуск
if __name__ == "__main__":
    print("🔍 Тестируем Google Trends API...")
    res = fetch_google_trends(region="RU", topic="нейросети", period="7d", max_results=5)
    
    if res["success"]:
        print(f"✅ Успех! Найдено: {res['page_info']['total_results']}")
        for i, item in enumerate(res["items"], 1):
            print(f"{i}. {item['query']} (интерес: {item['volume']})")
    else:
        print(f"❌ {res['error']}")
