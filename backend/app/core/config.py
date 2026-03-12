import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.project_name = os.getenv("PROJECT_NAME", "ReDirect Traffic Control")
        self.api_v1_prefix = os.getenv("API_V1_PREFIX", "/api/v1")
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://redirect:redirect@db:5432/redirect",
        )
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.signal_min_green = int(os.getenv("SIGNAL_MIN_GREEN", "20"))
        self.signal_max_green = int(os.getenv("SIGNAL_MAX_GREEN", "90"))
        self.signal_update_interval = int(os.getenv("SIGNAL_UPDATE_INTERVAL", "30"))


settings = Settings()
