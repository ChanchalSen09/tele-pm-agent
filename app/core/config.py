"""Centralized Application Configuration System via Pydantic Settings v2."""

from enum import Enum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    """Application execution environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """Immutable Application Settings validated on startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Environment Configuration
    APP_ENV: AppEnvironment = Field(default=AppEnvironment.DEVELOPMENT)
    LOG_LEVEL: str = Field(default="INFO")
    DEBUG: bool = Field(default=False)

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: SecretStr = Field(
        default=SecretStr("123456789:ABCdefGHIjklMNOpqrsTUVwxyz"),
        description="Telegram API Token from BotFather",
    )
    TELEGRAM_WEBHOOK_SECRET: SecretStr = Field(
        default=SecretStr(""),
        description="Secret token for Telegram Webhook validation",
    )
    TELEGRAM_WEBHOOK_URL: str = Field(
        default="", description="Public HTTPS Webhook URL"
    )

    # Google Gemini AI Configuration
    GEMINI_API_KEY: SecretStr = Field(
        default=SecretStr("AIzaSyPlaceholderGeminiKey"),
        description="Primary Google Gemini API Access Key",
    )
    GEMINI_SECONDARY_API_KEY: SecretStr = Field(
        default=SecretStr(""),
        description="Secondary/Fallback Google Gemini API Access Key",
    )
    GEMINI_MODEL_NAME: str = Field(default="gemini-3.6-flash")
    GEMINI_TIMEOUT_SECONDS: float = Field(default=15.0)
    GEMINI_MAX_RETRIES: int = Field(default=3)

    def get_gemini_api_keys(self) -> list[str]:
        """Returns ordered list of configured non-empty Gemini API keys for failover."""
        keys: list[str] = []
        primary = self.GEMINI_API_KEY.get_secret_value().strip()
        if primary and primary != "AIzaSyPlaceholderGeminiKey":
            keys.append(primary)
        secondary = self.GEMINI_SECONDARY_API_KEY.get_secret_value().strip()
        if secondary and secondary not in keys:
            keys.append(secondary)
        return keys or ([primary] if primary else [])

    # Database & Cache Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_bot_db"
    )
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Rate Limiting & Performance Parameters
    RATE_LIMIT_MESSAGES_PER_MIN: int = Field(default=10)

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == AppEnvironment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == AppEnvironment.TESTING


# Cached global settings instance loaded on boot
settings = Settings()
