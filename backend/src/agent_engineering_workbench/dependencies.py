from agent_engineering_workbench.adapter import WorkbenchAdapter


def get_web_research_adapter() -> WorkbenchAdapter:
    raise RuntimeError("Production web research adapter is not configured")
