"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/instantly"

    # JWT
    secret_key: str = "change-me-in-production-use-32-char-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # OpenAI
    openai_api_key: str = "sk-placeholder"
    openai_model: str = "gpt-4"
    openai_timeout: float = 30.0
    openai_max_retries: int = 3

    # Email sending
    email_max_retries: int = 3
    email_retry_wait_seconds: float = 2.0

    # Mailivery (warmup service)
    mailivery_api_key: str = ""
    mailivery_base_url: str = "https://app.mailivery.io/api/v1"

    # App
    app_name: str = "Instantly.ai API"
    debug: bool = False
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


settings = Settings()
