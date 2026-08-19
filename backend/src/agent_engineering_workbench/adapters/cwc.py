from collections.abc import Callable, Sequence
from typing import Protocol, cast

from context_window_compressor import (  # type: ignore[import-untyped]
    ApproximateTokenCounter,
    CompressionConfig,
    CompressionStrategy,
    ContextWindowCompressor,
    Message,
    NoCompressionStrategy,
    TruncationStrategy,
    WindowedCompressionStrategy,
)
from context_window_compressor.exceptions import (  # type: ignore[import-untyped]
    TokenBudgetError,
)

from agent_engineering_workbench.context_contracts import (
    ContextCompressionInput,
    ContextCompressionResult,
    ContextCompressionStrategy,
    ContextMessage,
)


class CWCProtocolError(RuntimeError):
    """Raised when CWC returns data outside the Workbench boundary."""


class ContextBudgetError(ValueError):
    """Raised when requested context budgets cannot be satisfied."""


class CWCMessageLike(Protocol):
    @property
    def role(self) -> str: ...

    @property
    def content(self) -> str | None: ...


class CWCMetricsLike(Protocol):
    @property
    def original_token_count(self) -> int: ...

    @property
    def compressed_token_count(self) -> int: ...

    @property
    def reduced_token_count(self) -> int: ...

    @property
    def compression_ratio(self) -> float: ...

    @property
    def strategy_name(self) -> str: ...

    @property
    def execution_time(self) -> float: ...

    @property
    def compression_applied(self) -> bool: ...

    @property
    def compressed_message_count(self) -> int: ...

    @property
    def preserved_message_count(self) -> int: ...


class CWCResultLike(Protocol):
    @property
    def messages(self) -> Sequence[CWCMessageLike]: ...

    @property
    def metrics(self) -> CWCMetricsLike: ...


class CWCCompressorLike(Protocol):
    def compress(
        self,
        messages: Sequence[CWCMessageLike],
        current_query: str | None = None,
    ) -> CWCResultLike: ...


type CWCCompressorFactory = Callable[
    [ContextCompressionInput], CWCCompressorLike
]
type CWCMessageFactory = Callable[..., CWCMessageLike]


def _create_public_compressor(
    compression_input: ContextCompressionInput,
) -> CWCCompressorLike:
    token_counter = ApproximateTokenCounter()
    config = CompressionConfig(
        max_tokens=compression_input.max_token_budget,
        target_tokens=compression_input.target_token_budget,
    )
    strategy_factories: dict[
        ContextCompressionStrategy, Callable[[], CompressionStrategy]
    ] = {
        ContextCompressionStrategy.NO_COMPRESSION: NoCompressionStrategy,
        ContextCompressionStrategy.TRUNCATION: lambda: TruncationStrategy(
            token_counter
        ),
        ContextCompressionStrategy.WINDOWED: lambda: (
            WindowedCompressionStrategy(token_counter)
        ),
    }
    strategy = strategy_factories[compression_input.strategy]()
    return cast(
        CWCCompressorLike,
        ContextWindowCompressor(config, strategy, token_counter),
    )


def _create_public_message(*, role: str, content: str | None) -> CWCMessageLike:
    return Message(role=role, content=content)


class CWCAdapter:
    """Translate Workbench Context DTOs through CWC's public compress API."""

    def __init__(
        self,
        *,
        compressor_factory: CWCCompressorFactory = _create_public_compressor,
        message_factory: CWCMessageFactory = _create_public_message,
    ) -> None:
        self._compressor_factory = compressor_factory
        self._message_factory = message_factory

    def compress(
        self,
        compression_input: ContextCompressionInput,
    ) -> ContextCompressionResult:
        cwc_messages = tuple(
            self._message_factory(role=message.role, content=message.content)
            for message in compression_input.messages
        )
        try:
            compressor = self._compressor_factory(compression_input)
            # Context Lab needs one direct history transformation, so it uses
            # CWC's public compress() rather than the Agent request helper.
            cwc_result = compressor.compress(cwc_messages)
        except TokenBudgetError as exc:
            raise ContextBudgetError(str(exc)) from exc
        strategy = self._map_strategy(cwc_result.metrics.strategy_name)
        if strategy is not compression_input.strategy:
            raise CWCProtocolError(
                "CWC result strategy does not match the requested strategy"
            )

        return ContextCompressionResult(
            original_messages=compression_input.messages,
            compressed_messages=tuple(
                ContextMessage.model_validate(
                    {"role": message.role, "content": message.content}
                )
                for message in cwc_result.messages
            ),
            original_token_estimate=cwc_result.metrics.original_token_count,
            compressed_token_estimate=(
                cwc_result.metrics.compressed_token_count
            ),
            tokens_saved_estimate=cwc_result.metrics.reduced_token_count,
            compression_ratio=cwc_result.metrics.compression_ratio,
            strategy=strategy,
            duration_ms=cwc_result.metrics.execution_time * 1000,
            compression_applied=cwc_result.metrics.compression_applied,
            compressed_message_count=(
                cwc_result.metrics.compressed_message_count
            ),
            preserved_message_count=(
                cwc_result.metrics.preserved_message_count
            ),
        )

    @staticmethod
    def _map_strategy(strategy_name: str) -> ContextCompressionStrategy:
        try:
            return ContextCompressionStrategy(strategy_name)
        except ValueError as exc:
            raise CWCProtocolError(
                f"Unsupported CWC strategy: {strategy_name}"
            ) from exc
