from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_engineering_workbench import __version__
from agent_engineering_workbench.api import (
    context_router,
    github_router,
    research_router,
    resume_router,
)
from agent_engineering_workbench.api.resume import (
    handle_resume_configuration_error,
)
from agent_engineering_workbench.config import get_settings
from agent_engineering_workbench.resume_errors import (
    ResumeOptimizationConfigurationError,
)


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
app.include_router(context_router)
app.include_router(github_router)
app.include_router(resume_router)
app.add_exception_handler(
    ResumeOptimizationConfigurationError,
    handle_resume_configuration_error,
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)
