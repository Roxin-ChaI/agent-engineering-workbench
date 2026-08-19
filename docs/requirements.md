# Requirements

## Project Goal

`Agent Engineering Workbench` provides a unified Web UI, API, and adapter boundary for independently maintained AI engineering projects.

Version history:

- v0.1.0: Workbench Shell and WRA Web Research integration.
- v0.2.0: PKRA Knowledge Research integration while retaining WRA.
- v0.3.0: Context Lab and CWC integration while retaining both Research workspaces.

## v0.3.0 Scope

### Backend

- Python 3.12 and FastAPI Backend.
- Workbench-owned immutable Context request/result DTOs, separate from Research `RunResult`.
- `CWCAdapter` using CWC v0.1.0 public APIs.
- Formal CWC dependency fixed to Git tag `v0.1.0`.
- `POST /api/context/compress` with no Context SSE endpoint.
- Translation of public CWC `TokenBudgetError` into a Workbench Context domain error and HTTP 422.
- Deterministic Fake Context dependency override for local GUI integration.
- Existing WRA and PKRA REST/SSE behavior remains available.

### Frontend

- Context TypeScript request/result contract independent of Python and CWC types.
- `compressContext()` REST client.
- `/context` Context Lab route and navigation.
- Editable message-history JSON.
- `no_compression`, `truncation`, and `windowed` strategy selection.
- Distinct target and maximum token-budget controls.
- Original / Compressed message comparison.
- Estimated original, compressed, and saved token Metrics; compression ratio, strategy, and duration.
- English / Chinese text and Dark / Light theme compatibility.
- Client-side invalid JSON handling, loading protection, and a stable request error state.

### Integrated Projects

- `web-research-agent` v0.2.0.
- `production-knowledge-research-agent` v0.4.0.
- `context-window-compressor` v0.1.0.

All projects remain independent repositories. Workbench uses public Python APIs and adapter boundaries; it does not copy source or invoke project CLIs through subprocesses.

## Context Contract and Behavior

The request contains ordered messages, `target_token_budget`, `max_token_budget`, and one supported strategy. The result contains original/compressed messages, estimated token counts, estimated tokens saved, compression ratio, strategy, duration, `compression_applied`, compressed message count, and preserved message count.

Token counts are estimates, not exact provider-tokenizer counts. CWC runs locally and offline without an API key, database, model provider, or network call. `CWCAdapter` invokes public CWC `compress()` and translates the public result without recomputing Metrics.

In CWC v0.1.0, `compression_applied=true` means the threshold was reached and the compression pipeline executed; it does not guarantee that output messages or estimated token counts changed.

If protected fixed/recent messages cannot fit the maximum budget, the boundary is:

```text
CWC TokenBudgetError
→ Workbench Context domain error
→ HTTP 422
```

Unexpected exceptions are not converted into client validation failures.

## Research Contract and Streaming Boundaries

Research Frontends depend only on the Workbench `RunResult` contract. PKRA currently maps Answer, Iterations, Tool Calls, and Duration but has no lossless structured Activity Trace or Source/Evidence URL contract; successful Knowledge runs therefore return `trace = []` and `sources = []`.

WRA and PKRA use synchronous run boundaries. Research SSE emits `started`, executes the agent, replays available Trace afterward, then emits `completed`, `stopped`, or `error`. It is not native real-time Token/Tool streaming.

## Validation Baseline

- 168 Backend tests pass.
- Ruff, mypy strict, and pip check pass.
- Frontend ESLint and TypeScript checks pass.
- Fake Context GUI covers all three strategies, invalid JSON blocking before POST, bilingual UI, themes, and a clean browser console.
- Real Context REST/GUI covers no-op `45 → 45`, actual `114 → 69` truncation, TokenBudgetError → HTTP 422, and a clean browser console.
- The final v0.3.0 Next.js production build remains a manual release verification.

## Non Goals

- Context persistence or Context SSE.
- File upload or per-message token counts.
- Exact provider-tokenizer integration.
- Exposing private CWC partition/change reasons.
- LLM-based Context summarization or external API calls.
- Fabricating PKRA Activity Trace or parsing Sources/Evidence from Answer text.
- Native real-time Research Token/Tool streaming.
- Copying or reimplementing WRA, PKRA, or CWC internals.
- User accounts, cloud deployment, persisted Research history, multi-agent orchestration, or MCP integration.

## Known UX Limitation

The Context API returns useful budget detail with HTTP 422, but v0.3.0 Frontend displays only `Unable to compress this context.` This is a documented LOW finding, not a release blocker.
