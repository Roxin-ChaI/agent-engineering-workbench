from agent_engineering_workbench.config import Settings
from agent_engineering_workbench.deepseek_client import DeepSeekModelClient
from agent_engineering_workbench.model_client import ModelClient


def create_model_client(settings: Settings) -> ModelClient:
    if settings.model_provider != "deepseek":
        raise ValueError(f"Unsupported model provider: {settings.model_provider}")

    api_key = settings.deepseek_api_key
    if api_key is None or not api_key.strip():
        raise ValueError("DEEPSEEK_API_KEY is required for the DeepSeek provider")

    return DeepSeekModelClient(
        api_key=api_key.strip(),
        base_url=settings.deepseek_base_url,
    )
