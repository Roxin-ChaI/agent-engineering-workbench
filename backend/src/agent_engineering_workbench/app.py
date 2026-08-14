from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_engineering_workbench import __version__
from agent_engineering_workbench.api import research_router
from agent_engineering_workbench.config import get_settings


class HealthResponse(BaseModel):
    status: str
    version: str


app = FastAPI(
    title="Agent Engineering Workbench API",
    version=__version__,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(research_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)
