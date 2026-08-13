from dataclasses import dataclass

import pytest

from agent_engineering_workbench.deepseek_client import DeepSeekModelClient
from agent_engineering_workbench.models import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
)


@dataclass
class FakeResponseMessage:
    content: str | None


@dataclass
class FakeChoice:
    message: FakeResponseMessage


@dataclass
class FakeChatCompletion:
    choices: list[FakeChoice]


class FakeCompletions:
    def __init__(self, completion: FakeChatCompletion) -> None:
        self.completion = completion
        self.model: str | None = None
        self.messages: list[dict[str, str]] | None = None

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
    ) -> FakeChatCompletion:
        self.model = model
        self.messages = messages
        return self.completion


class FakeChat:
    def __init__(self, completions: FakeCompletions) -> None:
        self.completions = completions


class FakeSDKClient:
    def __init__(self, completion: FakeChatCompletion) -> None:
        self.completions = FakeCompletions(completion)
        self.chat = FakeChat(self.completions)


def make_request() -> ModelRequest:
    return ModelRequest(
        messages=(
            ModelMessage(role="system", content="Be concise"),
            ModelMessage(role="user", content="Answer this"),
        ),
        model="configured-model",
    )


def test_invoke_maps_request_and_returns_model_response() -> None:
    sdk_client = FakeSDKClient(
        FakeChatCompletion(
            choices=[FakeChoice(message=FakeResponseMessage(content="Result"))]
        )
    )
    client = DeepSeekModelClient(
        api_key="not-a-real-key",
        base_url="https://deepseek.example",
        client=sdk_client,
    )
    request = make_request()

    response = client.invoke(request)

    assert sdk_client.completions.model == "configured-model"
    assert sdk_client.completions.messages == [
        {"role": "system", "content": "Be concise"},
        {"role": "user", "content": "Answer this"},
    ]
    assert response == ModelResponse(content="Result", model="configured-model")


def test_invoke_does_not_modify_request() -> None:
    sdk_client = FakeSDKClient(
        FakeChatCompletion(
            choices=[FakeChoice(message=FakeResponseMessage(content="Result"))]
        )
    )
    client = DeepSeekModelClient("not-a-real-key", "https://deepseek.example", client=sdk_client)
    request = make_request()
    original_request = request.model_copy(deep=True)

    client.invoke(request)

    assert request == original_request


def test_invoke_rejects_response_without_choices() -> None:
    sdk_client = FakeSDKClient(FakeChatCompletion(choices=[]))
    client = DeepSeekModelClient("not-a-real-key", "https://deepseek.example", client=sdk_client)

    with pytest.raises(RuntimeError, match="contained no choices"):
        client.invoke(make_request())


@pytest.mark.parametrize("content", [None, "", "   "])
def test_invoke_rejects_empty_content(content: str | None) -> None:
    sdk_client = FakeSDKClient(
        FakeChatCompletion(choices=[FakeChoice(message=FakeResponseMessage(content))])
    )
    client = DeepSeekModelClient("not-a-real-key", "https://deepseek.example", client=sdk_client)

    with pytest.raises(RuntimeError, match="content was empty"):
        client.invoke(make_request())


def test_api_key_is_not_exposed_by_errors_or_repr() -> None:
    api_key = "sensitive-not-a-real-key"

    class FailingCompletions(FakeCompletions):
        def create(
            self,
            *,
            model: str,
            messages: list[dict[str, str]],
        ) -> FakeChatCompletion:
            raise RuntimeError(f"SDK failure using {api_key}: {messages}")

    sdk_client = FakeSDKClient(FakeChatCompletion(choices=[]))
    sdk_client.completions = FailingCompletions(FakeChatCompletion(choices=[]))
    sdk_client.chat = FakeChat(sdk_client.completions)
    client = DeepSeekModelClient(api_key, "https://deepseek.example", client=sdk_client)

    with pytest.raises(RuntimeError) as error:
        client.invoke(make_request())

    assert str(error.value) == "DeepSeek model invocation failed"
    assert api_key not in repr(client)
    assert api_key not in repr(error.value)
    assert "Answer this" not in repr(error.value)
