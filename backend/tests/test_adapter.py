from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.contracts import RunMetrics, RunResult, RunStatus


class FakeAdapter:
    def run(self, user_input: str) -> RunResult:
        return RunResult(
            status=RunStatus.COMPLETED,
            output=f"Result for: {user_input}",
            metrics=RunMetrics(),
        )


def run_adapter(adapter: WorkbenchAdapter, user_input: str) -> RunResult:
    return adapter.run(user_input)


def test_fake_adapter_satisfies_workbench_adapter_protocol() -> None:
    result = run_adapter(FakeAdapter(), "research topic")

    assert result == RunResult(
        status=RunStatus.COMPLETED,
        output="Result for: research topic",
        metrics=RunMetrics(),
    )
