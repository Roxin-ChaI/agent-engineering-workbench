from typing import Annotated

from fastapi import APIRouter, Depends

from agent_engineering_workbench.adapters.cwc import CWCAdapter
from agent_engineering_workbench.context_contracts import (
    ContextCompressionInput,
    ContextCompressionResult,
)
from agent_engineering_workbench.dependencies import (
    get_context_compression_adapter,
)

router = APIRouter(prefix="/api/context", tags=["context"])


@router.post("/compress", response_model=ContextCompressionResult)
async def compress_context(
    request: ContextCompressionInput,
    adapter: Annotated[
        CWCAdapter,
        Depends(get_context_compression_adapter),
    ],
) -> ContextCompressionResult:
    return adapter.compress(request)
