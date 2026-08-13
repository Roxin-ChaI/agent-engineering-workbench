from fastapi import FastAPI
from pydantic import BaseModel

from agent_engineering_workbench import __version__


class HealthResponse(BaseModel):
    status: str
    version: str


app = FastAPI(
    title="Agent Engineering Workbench API",
    version=__version__,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)
