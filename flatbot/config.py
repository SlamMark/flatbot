from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:////data/flatbot.db"
    rapidapi_key: str = ""
    telegram_token: str = ""
    telegram_chat_id: str = ""
    web_secret_key: str = "change-me-in-production"
    scan_interval_minutes: int = 30
    web_api_url: str = "http://web:8000"
    log_level: str = "INFO"
    mock_api: bool = False


settings = Settings()
