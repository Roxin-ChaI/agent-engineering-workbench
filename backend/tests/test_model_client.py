import pytest
from pydantic import ValidationError

from agent_engineering_workbench.config import Settings
from agent_engineering_workbench.model_client import ModelClient, ModelClientFactory
from agent_engineering_workbench.models import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
)


class FakeModelClient:
    def invoke(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(content="fake response", model=request.model)


def invoke_client(client: ModelClient, request: ModelRequest) -> ModelResponse:
    return client.invoke(request)


def test_valid_model_message() -> None:
    message = ModelMessage(role="user", content="Hello")

    assert message.role == "user"
    assert message.content == "Hello"


def test_invalid_role_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelMessage.model_validate({"role": "invalid", "content": "Hello"})


def test_model_request_preserves_message_order() -> None:
    first_message = ModelMessage(role="system", content="Instructions")
    second_message = ModelMessage(role="user", content="Question")

    request = ModelRequest(
        messages=(first_message, second_message),
        model="test-model",
    )

    assert request.messages == (first_message, second_message)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelResponse.model_validate(
            {"content": "response", "model": "test-model", "unknown": True}
        )


def test_fake_client_satisfies_model_client_protocol() -> None:
    request = ModelRequest(
        messages=(ModelMessage(role="user", content="Question"),),
        model="test-model",
    )

    response = invoke_client(FakeModelClient(), request)

    assert response == ModelResponse(content="fake response", model="test-model")


def test_factory_returns_fake_client() -> None:
    def create_fake_client(settings: Settings) -> ModelClient:
        del settings
        return FakeModelClient()

    factory: ModelClientFactory = create_fake_client

    client = factory(Settings())

    assert isinstance(client, FakeModelClient)
