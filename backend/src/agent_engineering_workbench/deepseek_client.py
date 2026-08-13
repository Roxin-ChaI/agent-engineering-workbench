from collections.abc import Sequence
from typing import Protocol, cast

from openai import OpenAI

from agent_engineering_workbench.models import ModelRequest, ModelResponse


class _ResponseMessage(Protocol):
    @property
    def content(self) -> str | None: ...


class _Choice(Protocol):
    @property
    def message(self) -> _ResponseMessage: ...


class _ChatCompletion(Protocol):
    @property
    def choices(self) -> Sequence[_Choice]: ...


class _Completions(Protocol):
    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
    ) -> _ChatCompletion: ...


class _Chat(Protocol):
    @property
    def completions(self) -> _Completions: ...


class CompatibleSDKClient(Protocol):
    @property
    def chat(self) -> _Chat: ...


class DeepSeekModelClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        client: CompatibleSDKClient | None = None,
    ) -> None:
        self._client = client or cast(
            CompatibleSDKClient,
            OpenAI(api_key=api_key, base_url=base_url),
        )

    def invoke(self, request: ModelRequest) -> ModelResponse:
        messages = [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ]

        try:
            completion = self._client.chat.completions.create(
                model=request.model,
                messages=messages,
            )
        except Exception:  # noqa: BLE001
            raise RuntimeError("DeepSeek model invocation failed") from None

        if not completion.choices:
            raise RuntimeError("DeepSeek model response contained no choices")

        content = completion.choices[0].message.content
        if content is None or not content.strip():
            raise RuntimeError("DeepSeek model response content was empty")

        return ModelResponse(content=content, model=request.model)
