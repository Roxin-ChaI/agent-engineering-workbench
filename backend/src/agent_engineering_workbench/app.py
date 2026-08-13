from fastapi import FastAPI
from pydantic import BaseModel

from agent_engineering_workbench import __version__
from agent_engineering_workbench.api import research_router


class HealthResponse(BaseModel):
    status: str
    version: str


app = FastAPI(
    title="Agent Engineering Workbench API",
    version=__version__,
)
app.include_router(research_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)
