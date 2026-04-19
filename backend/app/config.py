from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Saju MVP API"
    llm_provider: Literal["ollama", "groq"] = "ollama"
    prompts_db_path: str = "./prompts.sqlite3"
    admin_api_key: str | None = None
    enable_admin_prompts: bool = False

    rate_limit_enabled: bool = True
    llm_rate_limit_per_ip_per_hour: int = 6
    llm_rate_limit_global_per_minute: int = 25

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_timeout_seconds: float = 120.0
    ollama_temperature: float = 0.25
    ollama_format_mode: Literal["auto", "schema", "json", "none"] = "auto"
    ollama_num_predict: int = Field(default=4096, ge=256, le=32768)

    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.1-8b-instant"
    groq_api_key: str | None = None
    groq_timeout_seconds: float = 60.0
    groq_temperature: float = 0.25
    groq_response_format_mode: Literal["auto", "json_schema", "json_object", "none"] = "auto"
    groq_json_schema_strict: bool = True
    groq_max_completion_tokens: int = Field(default=4096, ge=256, le=65536)

    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")
    cors_origin_regex: str | None = (
        r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|"
        r"192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):3000$"
    )

    @field_validator("cors_origin_regex", mode="before")
    @classmethod
    def normalize_blank_regex(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
