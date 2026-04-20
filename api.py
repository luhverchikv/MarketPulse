import random

# 📌 Заглушки. В продакшене здесь будут вызовы pytrends, YouTube Data API, TikTok API и т.д.
def _mock_trend_generator(source, territory, topic, period):
    period_labels = {'1d': '24ч', '7d': '7 дней', '14d': '14 дней', '30d': '30 дней'}
    p = period_labels.get(period, '7 дней')
    
    if source == 'google':
        return [
            {'title': f'Рост запросов: {topic}', 'volume': random.randint(5_000, 120_000), 'period': p, 'link': f'https://trends.google.com/trends/explore?q={topic}&geo={territory}'},
            {'title': f'Связанный тренд: {topic} tools', 'volume': random.randint(2_000, 45_000), 'period': p, 'link': 'https://trends.google.com'}
        ]
    elif source == 'youtube':
        return [
            {'title': f'Видео: {topic} в 2026', 'views': random.randint(50_000, 900_000), 'channel': 'TechInsights', 'link': f'https://youtube.com/results?search_query={topic}'},
            {'title': f'Разбор: {topic} для продукта', 'views': random.randint(15_000, 300_000), 'channel': 'ProductLab', 'link': 'https://youtube.com'}
        ]
    return []

def fetch_all_trends(territory, topic, period):
    return {
        'google': _mock_trend_generator('google', territory, topic, period),
        'youtube': _mock_trend_generator('youtube', territory, topic, period)
    }

