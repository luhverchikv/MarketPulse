# config.py
from dataclasses import dataclass
from environs import Env
import sys
import os


@dataclass
class DatabaseConfig:
    path: str
    name: str


@dataclass
class TgBot:
    token: str
    owner_id: int | None = None


@dataclass
class SchedulerConfig:
    daily_digest_time: str = "09:00"
    enabled: bool = True


@dataclass
class AppConfig:
    project_name: str = "TrendScope"
    debug: bool = False
    default_territory: str = "RU"
    default_topic: str = "AI / Tech"
    default_period: str = "7d"


@dataclass
class Config:
    bot: TgBot
    db: DatabaseConfig
    scheduler: SchedulerConfig
    app: AppConfig
    youtube: YouTubeConfig

@dataclass
class YouTubeConfig:
    api_key: str

# =============================================================================
env = Env()
if not any("pytest" in arg for arg in sys.argv):
    env.read_env()

db_path = env("DB_PATH", "data")
os.makedirs(db_path, exist_ok=True)

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
        project_name=env.str("PROJECT_NAME", "TrendScope"),
        debug=env.bool("DEBUG", False),
        default_territory=env.str("DEFAULT_TERRITORY", "RU"),
        default_topic=env.str("DEFAULT_TOPIC", "AI / Tech"),
        default_period=env.str("DEFAULT_PERIOD", "7d")
    ),
    youtube=YouTubeConfig(
        api_key=env.str("YOUTUBE_API_KEY", ""))
)

DB_FULL_PATH = os.path.join(config.db.path, config.db.name)

