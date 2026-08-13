from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator

from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.contracts import RunResult
from agent_engineering_workbench.dependencies import get_web_research_adapter


class WebResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("query must not be empty")
        return normalized_value


router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/web", response_model=RunResult)
async def run_web_research(
    request: WebResearchRequest,
    adapter: Annotated[WorkbenchAdapter, Depends(get_web_research_adapter)],
) -> RunResult:
    return adapter.run(request.query)
