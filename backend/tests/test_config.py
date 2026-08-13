from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from agent_engineering_workbench.config import Settings, get_settings

SETTINGS_ENVIRONMENT_VARIABLES = (
    "MODEL_PROVIDER",
    "MODEL_NAME",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
)


@pytest.fixture(autouse=True)
def isolate_settings_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for variable_name in SETTINGS_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_default_settings() -> None:
    settings = Settings()

    assert settings.model_provider == "deepseek"
    assert settings.model_name == "deepseek-v4-flash"
    assert settings.deepseek_base_url == "https://api.deepseek.com"


def test_environment_variables_override_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "configured-provider")
    monkeypatch.setenv("MODEL_NAME", "configured-model")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "configured-api-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://deepseek.example")

    settings = Settings()

    assert settings.model_provider == "configured-provider"
    assert settings.model_name == "configured-model"
    assert settings.deepseek_api_key == "configured-api-key"
    assert settings.deepseek_base_url == "https://deepseek.example"


def test_empty_provider_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "   ")

    with pytest.raises(ValidationError):
        Settings()


def test_empty_model_name_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_NAME", "   ")

    with pytest.raises(ValidationError):
        Settings()


def test_base_url_trailing_slashes_are_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com///")

    settings = Settings()

    assert settings.deepseek_base_url == "https://api.deepseek.com"


def test_api_key_is_excluded_from_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    api_key = "not-a-real-api-key"
    monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)

    settings = Settings()

    assert api_key not in repr(settings)
