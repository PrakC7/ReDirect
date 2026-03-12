import os

from dotenv import load_dotenv

load_dotenv()


def _split_origins(raw_value: str | None, fallback: list[str]) -> list[str]:
    if not raw_value:
        return fallback
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


class Settings:
    def __init__(self) -> None:
        self.project_name = os.getenv("PROJECT_NAME", "ReDirect Traffic Control")
        self.api_v1_prefix = os.getenv("API_V1_PREFIX", "/api/v1")
        self.frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
        self.allowed_origins = _split_origins(
            os.getenv("ALLOWED_ORIGINS"), [self.frontend_origin]
        )
        self.signal_min_green = int(os.getenv("SIGNAL_MIN_GREEN", "20"))
        self.signal_max_green = int(os.getenv("SIGNAL_MAX_GREEN", "90"))
        self.signal_update_interval = int(os.getenv("SIGNAL_UPDATE_INTERVAL", "30"))
        self.emergency_ttl_seconds = int(os.getenv("EMERGENCY_TTL_SECONDS", "900"))
        self.gov_api_key = os.getenv("GOV_API_KEY", "redirect-demo-key")


settings = Settings()
