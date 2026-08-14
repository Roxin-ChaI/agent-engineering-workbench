from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    model_provider: str = "deepseek"
    model_name: str = "deepseek-v4-flash"
    deepseek_api_key: str | None = Field(default=None, repr=False)
    deepseek_base_url: str = "https://api.deepseek.com"
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    @field_validator("model_provider", "model_name")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("must not be empty")
        return normalized_value

    @field_validator("deepseek_base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("cors_origins must not be empty")

        normalized_origins = tuple(origin.strip() for origin in value)
        if any(not origin for origin in normalized_origins):
            raise ValueError("CORS origins must not be empty")
        if "*" in normalized_origins:
            raise ValueError("wildcard CORS origins are not allowed")
        return normalized_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
