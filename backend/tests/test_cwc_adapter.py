from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass

import pytest

import agent_engineering_workbench.adapters.cwc as cwc_adapter_module
from agent_engineering_workbench.adapters.cwc import (
    CWCAdapter,
    CWCMessageLike,
    CWCProtocolError,
    CWCResultLike,
)
from agent_engineering_workbench.context_contracts import (
    ContextCompressionInput,
    ContextCompressionStrategy,
    ContextMessage,
)


@dataclass(frozen=True)
class FakeCWCMessage:
    role: str
    content: str | None = None


@dataclass(frozen=True)
class FakeCWCMetrics:
    original_token_count: int = 100
    compressed_token_count: int = 40
    reduced_token_count: int = 60
    compression_ratio: float = 0.4
    strategy_name: str = "truncation"
    execution_time: float = 0.125
    compression_applied: bool = True
    compressed_message_count: int = 2
    preserved_message_count: int = 1


@dataclass(frozen=True)
class FakeCWCResult:
    messages: tuple[FakeCWCMessage, ...]
    metrics: FakeCWCMetrics


class FakeCompressor:
    def __init__(self, result: CWCResultLike) -> None:
        self.result = result
        self.calls: list[tuple[CWCMessageLike, ...]] = []

    def compress(
        self,
        messages: Sequence[CWCMessageLike],
        current_query: str | None = None,
    ) -> CWCResultLike:
        assert current_query is None
        self.calls.append(tuple(messages))
        return self.result


class FakeFactories:
    def __init__(self, result: CWCResultLike) -> None:
        self.compressor = FakeCompressor(result)
        self.inputs: list[ContextCompressionInput] = []
        self.message_arguments: list[tuple[str, str | None]] = []

    def create_compressor(
        self,
        compression_input: ContextCompressionInput,
    ) -> FakeCompressor:
        self.inputs.append(compression_input)
        return self.compressor

    def create_message(self, *, role: str, content: str | None) -> FakeCWCMessage:
        self.message_arguments.append((role, content))
        return FakeCWCMessage(role=role, content=content)


def make_input(
    *,
    messages: tuple[ContextMessage, ...] = (
        ContextMessage(role="system", content="rules"),
        ContextMessage(role="user", content="question"),
    ),
    strategy: ContextCompressionStrategy = ContextCompressionStrategy.TRUNCATION,
) -> ContextCompressionInput:
    return ContextCompressionInput(
        messages=messages,
        target_token_budget=80,
        max_token_budget=100,
        strategy=strategy,
    )


def make_result(
    *,
    messages: tuple[FakeCWCMessage, ...] = (
        FakeCWCMessage(role="assistant", content="compressed history"),
    ),
    strategy_name: str = "truncation",
) -> FakeCWCResult:
    return FakeCWCResult(
        messages=messages,
        metrics=FakeCWCMetrics(strategy_name=strategy_name),
    )


def make_adapter(factories: FakeFactories) -> CWCAdapter:
    return CWCAdapter(
        compressor_factory=factories.create_compressor,
        message_factory=factories.create_message,
    )


@pytest.mark.parametrize(
    "messages",
    (
        (),
        (ContextMessage(role="user", content="hello"),),
    ),
)
def test_empty_and_simple_messages_are_mapped(
    messages: tuple[ContextMessage, ...],
) -> None:
    factories = FakeFactories(make_result())

    make_adapter(factories).compress(make_input(messages=messages))

    assert factories.message_arguments == [
        (message.role, message.content) for message in messages
    ]


def test_message_order_role_and_content_are_preserved() -> None:
    messages = (
        ContextMessage(role="system", content="rules"),
        ContextMessage(role="user", content="first"),
        ContextMessage(role="assistant", content="second"),
    )
    factories = FakeFactories(make_result())

    make_adapter(factories).compress(make_input(messages=messages))

    assert factories.message_arguments == [
        ("system", "rules"),
        ("user", "first"),
        ("assistant", "second"),
    ]
    assert [message.role for message in factories.compressor.calls[0]] == [
        "system",
        "user",
        "assistant",
    ]


def test_distinct_token_budgets_are_passed_to_factory() -> None:
    factories = FakeFactories(make_result())

    make_adapter(factories).compress(make_input())

    assert len(factories.inputs) == 1
    assert factories.inputs[0].target_token_budget == 80
    assert factories.inputs[0].max_token_budget == 100


def test_default_factory_maps_distinct_budgets_to_public_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factories = FakeFactories(make_result())
    config_arguments: list[tuple[int, int]] = []

    def create_config(*, max_tokens: int, target_tokens: int) -> object:
        config_arguments.append((max_tokens, target_tokens))
        return object()

    def create_compressor(
        config: object, strategy: object, token_counter: object
    ) -> FakeCompressor:
        del config, strategy, token_counter
        return factories.compressor

    monkeypatch.setattr(cwc_adapter_module, "CompressionConfig", create_config)
    monkeypatch.setattr(
        cwc_adapter_module, "ContextWindowCompressor", create_compressor
    )
    adapter = CWCAdapter(message_factory=factories.create_message)

    adapter.compress(make_input())

    assert config_arguments == [(100, 80)]


@pytest.mark.parametrize("strategy", tuple(ContextCompressionStrategy))
def test_all_public_strategies_are_mapped(
    strategy: ContextCompressionStrategy,
) -> None:
    factories = FakeFactories(make_result(strategy_name=strategy.value))

    result = make_adapter(factories).compress(make_input(strategy=strategy))

    assert factories.inputs[0].strategy is strategy
    assert result.strategy is strategy


def test_public_compress_is_called_exactly_once() -> None:
    factories = FakeFactories(make_result())

    make_adapter(factories).compress(make_input())

    assert len(factories.compressor.calls) == 1


def test_result_messages_and_all_public_metrics_are_mapped() -> None:
    factories = FakeFactories(
        make_result(
            messages=(
                FakeCWCMessage(role="assistant", content="summary"),
                FakeCWCMessage(role="user", content="latest"),
            )
        )
    )
    compression_input = make_input()

    result = make_adapter(factories).compress(compression_input)

    assert result.original_messages == compression_input.messages
    assert result.compressed_messages == (
        ContextMessage(role="assistant", content="summary"),
        ContextMessage(role="user", content="latest"),
    )
    assert result.original_token_estimate == 100
    assert result.compressed_token_estimate == 40
    assert result.tokens_saved_estimate == 60
    assert result.compression_ratio == 0.4
    assert result.duration_ms == 125.0
    assert result.compression_applied is True
    assert result.compressed_message_count == 2
    assert result.preserved_message_count == 1


def test_unknown_result_strategy_fails_closed() -> None:
    factories = FakeFactories(make_result(strategy_name="unknown"))

    with pytest.raises(CWCProtocolError, match="Unsupported CWC strategy"):
        make_adapter(factories).compress(make_input())


def test_result_strategy_must_match_requested_strategy() -> None:
    factories = FakeFactories(make_result(strategy_name="windowed"))

    with pytest.raises(CWCProtocolError, match="does not match"):
        make_adapter(factories).compress(make_input())


def test_cwc_exception_is_propagated_unchanged() -> None:
    expected_error = RuntimeError("compression failed")

    class FailingCompressor:
        def compress(
            self,
            messages: Sequence[CWCMessageLike],
            current_query: str | None = None,
        ) -> CWCResultLike:
            del messages, current_query
            raise expected_error

    def create_failing_compressor(
        compression_input: ContextCompressionInput,
    ) -> FailingCompressor:
        del compression_input
        return FailingCompressor()

    adapter = CWCAdapter(compressor_factory=create_failing_compressor)

    with pytest.raises(RuntimeError) as error:
        adapter.compress(make_input())

    assert error.value is expected_error


def test_adapter_does_not_modify_caller_input_or_expose_cwc_objects() -> None:
    compression_input = make_input()
    snapshot = deepcopy(compression_input)
    factories = FakeFactories(make_result())

    result = make_adapter(factories).compress(compression_input)

    assert compression_input == snapshot
    assert all(
        isinstance(message, ContextMessage)
        for message in result.compressed_messages
    )
    assert "FakeCWC" not in repr(result)


@pytest.mark.parametrize("strategy", tuple(ContextCompressionStrategy))
def test_real_public_cwc_api_supports_every_strategy_offline(
    strategy: ContextCompressionStrategy,
) -> None:
    result = CWCAdapter().compress(make_input(messages=(), strategy=strategy))

    assert result.strategy is strategy
    assert result.original_token_estimate == 0
    assert result.compressed_token_estimate == 0
