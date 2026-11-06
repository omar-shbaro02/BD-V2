"""Configuration governance tests."""

import pytest
from pydantic import ValidationError

from vai_bd.config import AppEnvironment, Settings


def test_safe_defaults_disable_external_execution() -> None:
    settings = Settings(_env_file=None, app_env=AppEnvironment.TEST)

    assert settings.external_execution_allowed is False
    assert settings.openai_api_key is None
    assert settings.trace_include_sensitive_data is False


def test_external_execution_cannot_be_enabled() -> None:
    with pytest.raises(ValidationError, match="External execution is unauthorized"):
        Settings(_env_file=None, external_execution_allowed=True)


def test_local_live_requires_openai_credentials_and_model() -> None:
    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, app_env=AppEnvironment.LOCAL_LIVE)
    with pytest.raises(ValidationError, match="OPENAI_MODEL"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.LOCAL_LIVE,
            openai_api_key="test-key",
        )
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.LOCAL_LIVE,
        openai_api_key="test-key",
        openai_model="configured-model",
    )
    assert settings.openai_model == "configured-model"
