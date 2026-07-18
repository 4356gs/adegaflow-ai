"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    Secret values are represented with ``SecretStr`` so accidental string
    rendering does not expose them in logs or API responses.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="AdegaFlow AI API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="sqlite:///./data/adegaflow.db",
        alias="DATABASE_URL",
    )
    demo_seed_path: str = Field(
        default="data/seeds/demo_seed.json",
        alias="DEMO_SEED_PATH",
    )

    dashscope_api_key: SecretStr | None = Field(default=None, alias="DASHSCOPE_API_KEY")
    qwen_base_url: str = Field(
        default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        alias="QWEN_BASE_URL",
    )
    qwen_model: str = Field(default="qwen3.7-plus", alias="QWEN_MODEL")
    qwen_fallback_model: str = Field(default="qwen3.6-flash", alias="QWEN_FALLBACK_MODEL")
    qwen_timeout_seconds: PositiveInt = Field(default=30, alias="QWEN_TIMEOUT_SECONDS")
    qwen_max_retries: int = Field(default=2, ge=0, le=5, alias="QWEN_MAX_RETRIES")
    async_run_queue_capacity: int = Field(
        default=10, ge=1, le=100, alias="ASYNC_RUN_QUEUE_CAPACITY"
    )

    @property
    def qwen_configured(self) -> bool:
        """Return whether a non-empty Qwen API key is available."""

        if self.dashscope_api_key is None:
            return False
        return bool(self.dashscope_api_key.get_secret_value().strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object."""

    return Settings()
