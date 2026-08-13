from typing import Any

import pytest

from agent_engineering_workbench.config import Settings
from agent_engineering_workbench.deepseek_client import DeepSeekModelClient
from agent_engineering_workbench.model_factory import create_model_client


class FakeOpenAIClient:
    pass


def test_factory_creates_deepseek_client_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def create_fake_openai_client(**kwargs: Any) -> FakeOpenAIClient:
        assert kwargs == {
            "api_key": "not-a-real-key",
            "base_url": "https://api.deepseek.com",
        }
        return FakeOpenAIClient()

    monkeypatch.setattr(
        "agent_engineering_workbench.deepseek_client.OpenAI",
        create_fake_openai_client,
    )

    client = create_model_client(Settings(deepseek_api_key="not-a-real-key"))

    assert isinstance(client, DeepSeekModelClient)


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_factory_requires_deepseek_api_key(api_key: str | None) -> None:
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY is required"):
        create_model_client(Settings(deepseek_api_key=api_key))


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported model provider"):
        create_model_client(
            Settings(
                model_provider="unknown",
                deepseek_api_key="not-a-real-key",
            )
        )
