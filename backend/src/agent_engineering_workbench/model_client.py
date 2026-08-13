from collections.abc import Callable
from typing import Protocol

from agent_engineering_workbench.config import Settings
from agent_engineering_workbench.models import ModelRequest, ModelResponse


class ModelClient(Protocol):
    def invoke(self, request: ModelRequest) -> ModelResponse: ...


ModelClientFactory = Callable[[Settings], ModelClient]
