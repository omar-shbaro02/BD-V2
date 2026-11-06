"""Validated application configuration and governance-safe profiles."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    """Supported runtime profiles."""

    LOCAL = "local"
    LOCAL_LIVE = "local-live"
    TEST = "test"
    CONFORMITY = "conformity"


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnvironment = AppEnvironment.LOCAL
    app_name: str = "VAI Business Development Decision Intelligence"
    app_version: str = "0.1.0.dev0"
    database_url: str = "postgresql+psycopg://vai_bd:vai_bd@localhost:5432/vai_bd"

    openai_api_key: str | None = Field(default=None, repr=False)
    openai_model: str | None = None
    openai_agents_disable_tracing: bool = False
    trace_include_sensitive_data: bool = False

    external_execution_allowed: bool = False
    test_auth_signing_key: str | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def enforce_governance_profile(self) -> "Settings":
        """Fail closed when a non-execution profile attempts to enable execution."""
        if self.external_execution_allowed:
            raise ValueError(
                "External execution is unauthorized in the current implementation build"
            )
        if self.app_env is AppEnvironment.LOCAL_LIVE:
            if not self.openai_api_key:
                raise ValueError("local-live requires OPENAI_API_KEY")
            if not self.openai_model:
                raise ValueError("local-live requires OPENAI_MODEL")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process settings singleton."""
    return Settings()
