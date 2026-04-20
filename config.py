# config.py
from dataclasses import dataclass
from environs import Env
import sys
import os


@dataclass
class DatabaseConfig:
    """Настройки базы данных (SQLite)"""
    path: str
    name: str


@dataclass
class TgBot:
    """Настройки Telegram-бота"""
    token: str
    owner_id: int | None = None


@dataclass
class SchedulerConfig:
    """Настройки планировщика"""
    daily_digest_time: str = "09:00"
    enabled: bool = True


@dataclass
class AppConfig:
    """Общие настройки приложения"""
    project_name: str = "MarketPulse"
    debug: bool = False
    default_territory: str = "RU"
    default_topic: str = "AI / Tech"
    default_period: str = "7d"


@dataclass
class YouTubeConfig:
    """Настройки YouTube API"""
    api_key: str


@dataclass
class Config:
    """Корневой конфиг приложения"""
    bot: TgBot
    db: DatabaseConfig
    scheduler: SchedulerConfig
    app: AppConfig
    youtube: YouTubeConfig  # Теперь YouTubeConfig уже определён выше


# =============================================================================
# Инициализация
# =============================================================================
env = Env()

# Не читаем .env при запуске тестов (pytest)
if not any("pytest" in arg for arg in sys.argv):
    env.read_env()

# Создаём директорию для БД, если не существует
db_path = env("DB_PATH", "data")
os.makedirs(db_path, exist_ok=True)

# Собираем конфиг
config = Config(
    bot=TgBot(
        token=env.str("BOT_TOKEN"),
        owner_id=env.int("OWNER_ID", None)
    ),
    db=DatabaseConfig(
        path=db_path,
        name=env.str("DB_NAME", "trendscope.db")
    ),
    scheduler=SchedulerConfig(
        daily_digest_time=env.str("DIGEST_TIME", "09:00"),
        enabled=env.bool("SCHEDULER_ENABLED", True)
    ),
    app=AppConfig(
        project_name=env.str("PROJECT_NAME", "MarketPulse"),
        debug=env.bool("DEBUG", False),
        default_territory=env.str("DEFAULT_TERRITORY", "RU"),
        default_topic=env.str("DEFAULT_TOPIC", "AI / Tech"),
        default_period=env.str("DEFAULT_PERIOD", "7d")
    ),
    youtube=YouTubeConfig(
        api_key=env.str("YOUTUBE_API_KEY", "")
    )
)

# Полный путь к файлу БД
DB_FULL_PATH = os.path.join(config.db.path, config.db.name)
