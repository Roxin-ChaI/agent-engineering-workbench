from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from agent_engineering_workbench.config import Settings, get_settings

SETTINGS_ENVIRONMENT_VARIABLES = (
    "MODEL_PROVIDER",
    "MODEL_NAME",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_TIMEOUT_SECONDS",
    "PROMPT_VAULT_BASE_URL",
    "PROMPT_VAULT_TIMEOUT_SECONDS",
    "PKRA_DATABASE_URL",
    "PKRA_ENABLE_WEB_SEARCH",
    "CORS_ORIGINS",
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
    assert settings.deepseek_timeout_seconds == 60.0
    assert settings.prompt_vault_base_url == "http://127.0.0.1:8000"
    assert settings.prompt_vault_timeout_seconds == 10.0
    assert settings.pkra_database_url is None
    assert settings.pkra_enable_web_search is True
    assert settings.cors_origins == (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )


def test_environment_variables_override_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "configured-provider")
    monkeypatch.setenv("MODEL_NAME", "configured-model")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "configured-api-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://deepseek.example")
    monkeypatch.setenv("DEEPSEEK_TIMEOUT_SECONDS", "27.5")
    monkeypatch.setenv("PROMPT_VAULT_BASE_URL", "https://vault.example/")
    monkeypatch.setenv("PROMPT_VAULT_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv(
        "PKRA_DATABASE_URL",
        " postgresql+psycopg://user:password@localhost/research ",
    )
    monkeypatch.setenv("PKRA_ENABLE_WEB_SEARCH", "false")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        '[" https://frontend.example ","http://127.0.0.1:4000"]',
    )

    settings = Settings()

    assert settings.model_provider == "configured-provider"
    assert settings.model_name == "configured-model"
    assert settings.deepseek_api_key == "configured-api-key"
    assert settings.deepseek_base_url == "https://deepseek.example"
    assert settings.deepseek_timeout_seconds == 27.5
    assert settings.prompt_vault_base_url == "https://vault.example"
    assert settings.prompt_vault_timeout_seconds == 12.5
    assert (
        settings.pkra_database_url
        == "postgresql+psycopg://user:password@localhost/research"
    )
    assert settings.pkra_enable_web_search is False
    assert settings.cors_origins == (
        "https://frontend.example",
        "http://127.0.0.1:4000",
    )


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


def test_non_positive_deepseek_timeout_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_TIMEOUT_SECONDS", "0")

    with pytest.raises(ValidationError):
        Settings()


def test_prompt_vault_base_url_trailing_slashes_are_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROMPT_VAULT_BASE_URL", "http://127.0.0.1:8000///")

    settings = Settings()

    assert settings.prompt_vault_base_url == "http://127.0.0.1:8000"


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_prompt_vault_base_url_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("PROMPT_VAULT_BASE_URL", value)

    with pytest.raises(ValidationError):
        Settings()


def test_non_positive_prompt_vault_timeout_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROMPT_VAULT_TIMEOUT_SECONDS", "0")

    with pytest.raises(ValidationError):
        Settings()


def test_api_key_is_excluded_from_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    api_key = "not-a-real-api-key"
    monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)

    settings = Settings()

    assert api_key not in repr(settings)


def test_pkra_database_url_is_excluded_from_repr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = "postgresql+psycopg://user:secret@localhost/research"
    monkeypatch.setenv("PKRA_DATABASE_URL", database_url)

    settings = Settings()

    assert database_url not in repr(settings)


def test_empty_pkra_database_url_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PKRA_DATABASE_URL", "   ")

    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize(
    "origins",
    ["[]", '["   "]'],
)
def test_empty_cors_origins_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    origins: str,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", origins)

    with pytest.raises(ValidationError):
        Settings()


def test_wildcard_cors_origin_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["*"]')

    with pytest.raises(ValidationError):
        Settings()
