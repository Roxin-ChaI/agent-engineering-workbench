from typing import Never

import pytest

from agent_engineering_workbench import dependencies
from agent_engineering_workbench.adapters.wra import WRAAdapter
from agent_engineering_workbench.config import Settings


class FakeAgent:
    def __init__(self, model_client: object, web_search_tool: object) -> None:
        self.model_client = model_client
        self.web_search_tool = web_search_tool

    def run(self, question: str) -> Never:
        raise AssertionError(f"FakeAgent.run must not be called: {question}")


def test_default_deepseek_provider_is_assembled_from_wra_public_factories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "not-a-real-key"
    fake_model = object()
    fake_tool = object()
    captured: dict[str, object] = {}

    def fake_model_factory(api_key: str, *, model: str) -> object:
        captured["api_key"] = api_key
        captured["model_name"] = model
        return fake_model

    def fake_search_tool_factory() -> object:
        captured["search_factory_called"] = True
        return fake_tool

    class CapturingAgent(FakeAgent):
        def __init__(self, model_client: object, web_search_tool: object) -> None:
            super().__init__(model_client, web_search_tool)
            captured["agent_model"] = model_client
            captured["agent_tool"] = web_search_tool

    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(deepseek_api_key=secret),
    )
    monkeypatch.setattr(dependencies, "create_deepseek_model", fake_model_factory)
    monkeypatch.setattr(
        dependencies,
        "DDGSWebSearchTool",
        fake_search_tool_factory,
    )
    monkeypatch.setattr(dependencies, "WebResearchAgent", CapturingAgent)

    adapter = dependencies.get_web_research_adapter()

    assert isinstance(adapter, WRAAdapter)
    assert captured == {
        "api_key": secret,
        "model_name": "deepseek-v4-flash",
        "search_factory_called": True,
        "agent_model": fake_model,
        "agent_tool": fake_tool,
    }
    assert secret not in repr(adapter)


def test_configured_model_name_is_passed_to_wra_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_model_names: list[str] = []

    def fake_model_factory(api_key: str, *, model: str) -> object:
        assert api_key == "not-a-real-key"
        captured_model_names.append(model)
        return object()

    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            model_name="configured-model",
            deepseek_api_key="not-a-real-key",
        ),
    )
    monkeypatch.setattr(dependencies, "create_deepseek_model", fake_model_factory)
    monkeypatch.setattr(dependencies, "DDGSWebSearchTool", object)
    monkeypatch.setattr(dependencies, "WebResearchAgent", FakeAgent)

    adapter = dependencies.get_web_research_adapter()

    assert isinstance(adapter, WRAAdapter)
    assert captured_model_names == ["configured-model"]


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_deepseek_api_key_is_required(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(deepseek_api_key=api_key),
    )

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY is required"):
        dependencies.get_web_research_adapter()


def test_unknown_provider_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            model_provider="unknown",
            deepseek_api_key="not-a-real-key",
        ),
    )

    with pytest.raises(ValueError, match="Unsupported model provider: unknown"):
        dependencies.get_web_research_adapter()
