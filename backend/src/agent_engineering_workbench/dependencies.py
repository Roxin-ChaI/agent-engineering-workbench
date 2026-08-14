from web_research_agent.agent import WebResearchAgent  # type: ignore[import-untyped]
from web_research_agent.llm import (  # type: ignore[import-untyped]
    create_deepseek_model,
)
from web_research_agent.tools import (  # type: ignore[import-untyped]
    DDGSWebSearchTool,
)

from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.adapters.wra import WRAAdapter
from agent_engineering_workbench.config import get_settings


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
