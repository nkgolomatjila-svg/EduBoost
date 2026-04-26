"""
EduBoost SA — Application Configuration
All settings loaded from environment variables via Pydantic Settings
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_SECRETS = {
    "change-me",
    "change-me-32-chars-exactly!!!!!!",
    "change-me-salt",
    "devpassword",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_ENV: str = "development"
    APP_NAME: str = "EduBoost SA"
    APP_VERSION: str = "1.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://eduboost_user:devpassword@localhost:5432/eduboost"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "eduboost"
    POSTGRES_USER: str = "eduboost_user"
    POSTGRES_PASSWORD: str = "devpassword"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""

    # AI — Primary
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-70b-8192"
    GROQ_MAX_TOKENS: int = 1800
    GROQ_TEMPERATURE: float = 0.65
    GROQ_TIMEOUT_SECONDS: int = 30

    # AI — Secondary
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 1800

    # AI — Fallback
    HUGGINGFACE_API_KEY: str = ""
    HUGGINGFACE_MODEL: str = "HuggingFaceH4/zephyr-7b-beta"

    # Security
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    ENCRYPTION_KEY: str = ""
    ENCRYPTION_SALT: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://eduboost.co.za"]

    # Monitoring
    SENTRY_DSN: str = ""
    PROMETHEUS_ENABLED: bool = True

    # Feature flags
    FEATURE_VOICE_INPUT: bool = True
    FEATURE_OFFLINE_MODE: bool = True
    FEATURE_PARENT_REPORTS: bool = True
    FEATURE_RLHF_COLLECTION: bool = True
    FEATURE_LEARNING_STYLE_ML: bool = True

    # Rate limiting
    RATE_LIMIT_LLM_PER_MINUTE: int = 20
    RATE_LIMIT_API_PER_MINUTE: int = 100
    GROQ_DAILY_REQUEST_LIMIT: int = 14400

    # Fourth Estate / Constitutional Audit
    FOURTH_ESTATE_STREAM_KEY: str = "eduboost:audit_stream"
    FOURTH_ESTATE_MAX_LEN: int = 100000
    ETHER_PROFILE_TTL: int = 86400

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        allowed = {"development", "test", "staging", "production"}
        normalized = value.lower().strip()
        if normalized not in allowed:
            raise ValueError(f"APP_ENV must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.APP_ENV != "production":
            return self

        required_non_empty = {
            "SECRET_KEY": self.SECRET_KEY,
            "JWT_SECRET": self.JWT_SECRET,
            "ENCRYPTION_KEY": self.ENCRYPTION_KEY,
            "ENCRYPTION_SALT": self.ENCRYPTION_SALT,
            "DATABASE_URL": self.DATABASE_URL,
        }

        missing = [key for key, value in required_non_empty.items() if not value or not value.strip()]
        if missing:
            raise ValueError(f"Missing required production settings: {', '.join(missing)}")

        placeholder_values = [
            key
            for key, value in required_non_empty.items()
            if value in _PLACEHOLDER_SECRETS or "devpassword" in value
        ]
        if placeholder_values:
            raise ValueError(
                "Refusing to start in production with placeholder or development secrets: "
                + ", ".join(placeholder_values)
            )

        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
