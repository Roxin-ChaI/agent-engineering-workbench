import pytest
from pydantic import ValidationError

from agent_engineering_workbench.context_contracts import (
    ContextCompressionInput,
    ContextCompressionResult,
    ContextCompressionStrategy,
    ContextMessage,
)


def test_context_input_preserves_message_order_and_distinct_budgets() -> None:
    messages = (
        ContextMessage(role="system", content="rules"),
        ContextMessage(role="user", content="question"),
    )

    compression_input = ContextCompressionInput(
        messages=messages,
        target_token_budget=80,
        max_token_budget=100,
        strategy=ContextCompressionStrategy.TRUNCATION,
    )

    assert compression_input.messages == messages
    assert compression_input.target_token_budget == 80
    assert compression_input.max_token_budget == 100


def test_target_budget_must_not_exceed_maximum() -> None:
    with pytest.raises(ValidationError, match="must not exceed"):
        ContextCompressionInput(
            messages=(),
            target_token_budget=101,
            max_token_budget=100,
            strategy=ContextCompressionStrategy.WINDOWED,
        )


def test_unknown_strategy_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ContextCompressionInput.model_validate(
            {
                "messages": [],
                "target_token_budget": 80,
                "max_token_budget": 100,
                "strategy": "unknown",
            }
        )


def test_context_contracts_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ContextMessage.model_validate(
            {"role": "user", "content": "question", "unknown": True}
        )


def test_result_rejects_inconsistent_estimated_metrics() -> None:
    with pytest.raises(ValidationError, match="tokens_saved_estimate"):
        ContextCompressionResult(
            original_messages=(),
            compressed_messages=(),
            original_token_estimate=100,
            compressed_token_estimate=40,
            tokens_saved_estimate=59,
            compression_ratio=0.4,
            strategy=ContextCompressionStrategy.TRUNCATION,
            duration_ms=1.0,
            compression_applied=True,
            compressed_message_count=2,
            preserved_message_count=1,
        )
