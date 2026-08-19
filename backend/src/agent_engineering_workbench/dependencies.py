from collections.abc import Iterator
from typing import Protocol, cast

from web_research_agent.agent import WebResearchAgent  # type: ignore[import-untyped]
from web_research_agent.llm import (  # type: ignore[import-untyped]
    create_deepseek_model,
)
from web_research_agent.tools import (  # type: ignore[import-untyped]
    DDGSWebSearchTool,
)

from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.adapters.cwc import CWCAdapter
from agent_engineering_workbench.adapters.pkra import (
    PKRAAdapter,
    PKRARunner,
)
from agent_engineering_workbench.adapters.wra import WRAAdapter
from agent_engineering_workbench.config import Settings, get_settings


class _AgentRunnerConfigFactory(Protocol):
    def __call__(
        self,
        *,
        database_url: str,
        deepseek_api_key: str,
        model_name: str,
        enable_web_search: bool,
    ) -> object: ...


class _ClosablePKRARunner(PKRARunner, Protocol):
    def close(self) -> None: ...


class _CreateAgentRunner(Protocol):
    def __call__(self, config: object) -> _ClosablePKRARunner: ...


def _load_pkra_public_api() -> tuple[
    _AgentRunnerConfigFactory,
    _CreateAgentRunner,
]:
    from research_agent import (  # type: ignore[import-not-found, import-untyped]
        AgentRunnerConfig,
        create_agent_runner,
    )

    return (
        cast(_AgentRunnerConfigFactory, AgentRunnerConfig),
        cast(_CreateAgentRunner, create_agent_runner),
    )


def _validate_pkra_settings(settings: Settings) -> tuple[str, str]:
    if settings.model_provider != "deepseek":
        raise ValueError(f"Unsupported model provider: {settings.model_provider}")

    database_url = settings.pkra_database_url
    if database_url is None:
        raise ValueError("PKRA_DATABASE_URL is required for knowledge research")

    api_key = settings.deepseek_api_key
    if api_key is None or not api_key.strip():
        raise ValueError("DEEPSEEK_API_KEY is required for knowledge research")
    return database_url, api_key.strip()


def get_web_research_adapter() -> WorkbenchAdapter:
    settings = get_settings()
    if settings.model_provider != "deepseek":
        raise ValueError(f"Unsupported model provider: {settings.model_provider}")

    api_key = settings.deepseek_api_key
    if api_key is None or not api_key.strip():
        raise ValueError("DEEPSEEK_API_KEY is required for the DeepSeek provider")

    model_client = create_deepseek_model(
        api_key=api_key.strip(),
        model=settings.model_name,
    )
    web_search_tool = DDGSWebSearchTool()
    agent = WebResearchAgent(
        model_client=model_client,
        web_search_tool=web_search_tool,
    )
    return WRAAdapter(agent)


def get_context_compression_adapter() -> CWCAdapter:
    return CWCAdapter()


def get_knowledge_research_adapter() -> Iterator[WorkbenchAdapter]:
    settings = get_settings()
    database_url, api_key = _validate_pkra_settings(settings)
    config_factory, runner_factory = _load_pkra_public_api()
    config = config_factory(
        database_url=database_url,
        deepseek_api_key=api_key,
        model_name=settings.model_name,
        enable_web_search=settings.pkra_enable_web_search,
    )
    runner = runner_factory(config)
    try:
        yield PKRAAdapter(runner)
    finally:
        runner.close()
