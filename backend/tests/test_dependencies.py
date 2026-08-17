from contextlib import contextmanager
from dataclasses import dataclass
from typing import Never

import pytest

from agent_engineering_workbench import dependencies
from agent_engineering_workbench.adapters.pkra import (
    PKRAAdapter,
    PKRAResultLike,
)
from agent_engineering_workbench.adapters.wra import WRAAdapter
from agent_engineering_workbench.config import Settings


class FakeAgent:
    def __init__(self, model_client: object, web_search_tool: object) -> None:
        self.model_client = model_client
        self.web_search_tool = web_search_tool

    def run(self, question: str) -> Never:
        raise AssertionError(f"FakeAgent.run must not be called: {question}")


@dataclass(frozen=True, repr=False)
class FakeAgentRunnerConfig:
    database_url: str
    deepseek_api_key: str
    model_name: str
    enable_web_search: bool

    def __repr__(self) -> str:
        return (
            "FakeAgentRunnerConfig(database_url=<redacted>, "
            "deepseek_api_key=<redacted>, "
            f"model_name={self.model_name!r}, "
            f"enable_web_search={self.enable_web_search!r})"
        )


class FakePKRARunner:
    def __init__(self) -> None:
        self.close_calls = 0

    def run(self, query: str) -> PKRAResultLike:
        raise AssertionError(f"FakePKRARunner.run must not be called: {query}")

    def close(self) -> None:
        self.close_calls += 1


def install_fake_pkra_public_api(
    monkeypatch: pytest.MonkeyPatch,
    *,
    runner: FakePKRARunner,
    captured_configs: list[FakeAgentRunnerConfig],
) -> None:
    def fake_create_agent_runner(config: object) -> FakePKRARunner:
        assert isinstance(config, FakeAgentRunnerConfig)
        captured_configs.append(config)
        return runner

    monkeypatch.setattr(
        dependencies,
        "_load_pkra_public_api",
        lambda: (FakeAgentRunnerConfig, fake_create_agent_runner),
    )


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


def test_knowledge_adapter_uses_public_factory_and_closes_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "not-a-real-key"
    runner = FakePKRARunner()
    captured_configs: list[FakeAgentRunnerConfig] = []
    install_fake_pkra_public_api(
        monkeypatch,
        runner=runner,
        captured_configs=captured_configs,
    )
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            model_name="configured-model",
            deepseek_api_key=secret,
            pkra_database_url="postgresql+psycopg://user:password@db/pkra",
            pkra_enable_web_search=False,
        ),
    )

    with contextmanager(dependencies.get_knowledge_research_adapter)() as adapter:
        assert isinstance(adapter, PKRAAdapter)
        assert runner.close_calls == 0

    assert runner.close_calls == 1
    assert captured_configs == [
        FakeAgentRunnerConfig(
            database_url="postgresql+psycopg://user:password@db/pkra",
            deepseek_api_key=secret,
            model_name="configured-model",
            enable_web_search=False,
        )
    ]
    assert secret not in repr(captured_configs[0])
    assert "user:password" not in repr(captured_configs[0])


def test_knowledge_runner_closes_when_adapter_scope_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakePKRARunner()
    install_fake_pkra_public_api(
        monkeypatch,
        runner=runner,
        captured_configs=[],
    )
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            deepseek_api_key="not-a-real-key",
            pkra_database_url="postgresql+psycopg://user:password@db/pkra",
        ),
    )
    expected = RuntimeError("adapter use failed")

    with (
        pytest.raises(RuntimeError) as exc_info,
        contextmanager(dependencies.get_knowledge_research_adapter)(),
    ):
        raise expected

    assert exc_info.value is expected
    assert runner.close_calls == 1


def test_knowledge_runner_creation_error_propagates_without_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = RuntimeError("runner creation failed")

    def fail_runner_creation(config: object) -> Never:
        assert isinstance(config, FakeAgentRunnerConfig)
        raise expected

    monkeypatch.setattr(
        dependencies,
        "_load_pkra_public_api",
        lambda: (FakeAgentRunnerConfig, fail_runner_creation),
    )
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            deepseek_api_key="not-a-real-key",
            pkra_database_url="postgresql+psycopg://user:password@db/pkra",
        ),
    )

    with (
        pytest.raises(RuntimeError) as exc_info,
        contextmanager(dependencies.get_knowledge_research_adapter)(),
    ):
        pass

    assert exc_info.value is expected


def test_knowledge_database_url_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(deepseek_api_key="not-a-real-key"),
    )

    with (
        pytest.raises(ValueError, match="PKRA_DATABASE_URL is required"),
        contextmanager(dependencies.get_knowledge_research_adapter)(),
    ):
        pass


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_knowledge_deepseek_api_key_is_required(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            deepseek_api_key=api_key,
            pkra_database_url="postgresql+psycopg://user:password@db/pkra",
        ),
    )

    with (
        pytest.raises(
            ValueError,
            match="DEEPSEEK_API_KEY is required",
        ) as exc_info,
        contextmanager(dependencies.get_knowledge_research_adapter)(),
    ):
        pass

    if api_key and api_key.strip():
        assert api_key not in str(exc_info.value)


def test_knowledge_unknown_provider_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            model_provider="unknown",
            deepseek_api_key="not-a-real-key",
            pkra_database_url="postgresql+psycopg://user:password@db/pkra",
        ),
    )

    with (
        pytest.raises(ValueError, match="Unsupported model provider: unknown"),
        contextmanager(dependencies.get_knowledge_research_adapter)(),
    ):
        pass
