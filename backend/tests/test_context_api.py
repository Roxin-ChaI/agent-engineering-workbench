from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agent_engineering_workbench.adapters.cwc import (
    ContextBudgetError,
    CWCAdapter,
)
from agent_engineering_workbench.app import app
from agent_engineering_workbench.context_contracts import (
    ContextCompressionInput,
    ContextCompressionResult,
    ContextCompressionStrategy,
    ContextMessage,
)
from agent_engineering_workbench.dependencies import (
    get_context_compression_adapter,
)


class FakeCWCAdapter:
    def __init__(self) -> None:
        self.inputs: list[ContextCompressionInput] = []

    def compress(
        self,
        compression_input: ContextCompressionInput,
    ) -> ContextCompressionResult:
        self.inputs.append(compression_input)
        return ContextCompressionResult(
            original_messages=compression_input.messages,
            compressed_messages=(
                ContextMessage(role="assistant", content="compressed summary"),
                compression_input.messages[-1],
            ),
            original_token_estimate=100,
            compressed_token_estimate=40,
            tokens_saved_estimate=60,
            compression_ratio=0.4,
            strategy=compression_input.strategy,
            duration_ms=2.5,
            compression_applied=True,
            compressed_message_count=2,
            preserved_message_count=1,
        )


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def valid_payload(
    strategy: str = "truncation",
) -> dict[str, object]:
    return {
        "messages": [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
            {"role": "user", "content": "latest question"},
        ],
        "target_token_budget": 80,
        "max_token_budget": 100,
        "strategy": strategy,
    }


@pytest.mark.parametrize("strategy", tuple(ContextCompressionStrategy))
def test_context_compression_returns_contract_for_every_strategy(
    strategy: ContextCompressionStrategy,
) -> None:
    adapter = FakeCWCAdapter()
    app.dependency_overrides[get_context_compression_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/context/compress",
        json=valid_payload(strategy.value),
    )

    assert response.status_code == 200
    assert response.json() == {
        "original_messages": [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
            {"role": "user", "content": "latest question"},
        ],
        "compressed_messages": [
            {"role": "assistant", "content": "compressed summary"},
            {"role": "user", "content": "latest question"},
        ],
        "original_token_estimate": 100,
        "compressed_token_estimate": 40,
        "tokens_saved_estimate": 60,
        "compression_ratio": 0.4,
        "strategy": strategy.value,
        "duration_ms": 2.5,
        "compression_applied": True,
        "compressed_message_count": 2,
        "preserved_message_count": 1,
    }
    assert len(adapter.inputs) == 1


def test_messages_and_budgets_are_passed_to_adapter_in_order() -> None:
    adapter = FakeCWCAdapter()
    app.dependency_overrides[get_context_compression_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/context/compress",
        json=valid_payload(),
    )

    assert response.status_code == 200
    assert [
        (message.role, message.content)
        for message in adapter.inputs[0].messages
    ] == [
        ("system", "rules"),
        ("user", "first question"),
        ("assistant", "first answer"),
        ("user", "latest question"),
    ]
    assert adapter.inputs[0].target_token_budget == 80
    assert adapter.inputs[0].max_token_budget == 100


@pytest.mark.parametrize(
    "payload",
    (
        {**valid_payload(), "messages": [{"role": "invalid", "content": "x"}]},
        {**valid_payload(), "target_token_budget": 0},
        {**valid_payload(), "target_token_budget": 101},
        {**valid_payload(), "strategy": "unknown"},
    ),
)
def test_invalid_context_request_returns_422(
    payload: dict[str, object],
) -> None:
    adapter = FakeCWCAdapter()
    app.dependency_overrides[get_context_compression_adapter] = lambda: adapter

    response = TestClient(app).post("/api/context/compress", json=payload)

    assert response.status_code == 422
    assert adapter.inputs == []


def test_adapter_exception_uses_existing_rest_error_semantics() -> None:
    expected_error = RuntimeError("compression failed")

    class FailingAdapter:
        def compress(
            self,
            compression_input: ContextCompressionInput,
        ) -> ContextCompressionResult:
            del compression_input
            raise expected_error

    app.dependency_overrides[get_context_compression_adapter] = FailingAdapter

    with pytest.raises(RuntimeError) as error:
        TestClient(app).post(
            "/api/context/compress",
            json=valid_payload(),
        )

    assert error.value is expected_error


def test_context_budget_error_returns_semantic_validation_response() -> None:
    class BudgetFailingAdapter:
        def compress(
            self,
            compression_input: ContextCompressionInput,
        ) -> ContextCompressionResult:
            del compression_input
            raise ContextBudgetError(
                "fixed and recent messages require 45 tokens; "
                "maximum budget is 40"
            )

    app.dependency_overrides[get_context_compression_adapter] = (
        BudgetFailingAdapter
    )

    response = TestClient(app).post(
        "/api/context/compress",
        json=valid_payload(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "fixed and recent messages require 45 tokens; "
            "maximum budget is 40"
        )
    }


def test_public_cwc_token_budget_error_returns_422() -> None:
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "This fixed message cannot fit one token.",
            }
        ],
        "target_token_budget": 1,
        "max_token_budget": 1,
        "strategy": "truncation",
    }

    response = TestClient(app).post("/api/context/compress", json=payload)

    assert response.status_code == 422
    assert response.json() == {
        "detail": "fixed messages require 15 tokens; maximum budget is 1"
    }


def test_response_excludes_research_only_fields() -> None:
    adapter = FakeCWCAdapter()
    app.dependency_overrides[get_context_compression_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/context/compress",
        json=valid_payload(),
    )

    assert response.status_code == 200
    assert {"status", "trace", "sources", "error"}.isdisjoint(response.json())


def test_production_dependency_creates_cwc_adapter() -> None:
    assert isinstance(get_context_compression_adapter(), CWCAdapter)


def test_existing_routes_remain_registered() -> None:
    paths = app.openapi()["paths"]

    assert "/api/context/compress" in paths
    assert "/health" in paths
    assert "/api/research/web" in paths
    assert "/api/research/knowledge" in paths
