from typing import Protocol

from agent_engineering_workbench.contracts import RunResult


class WorkbenchAdapter(Protocol):
    def run(self, user_input: str) -> RunResult: ...
