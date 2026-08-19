# Architecture

## Overall Architecture

```text
Browser
→ Next.js Frontend
→ Workbench FastAPI
→ Adapter boundary
    ├── WRAAdapter → WRA v0.2.0
    ├── PKRAAdapter → PKRA v0.4.0 ProductionAgentRunner
    │                    → PostgreSQL / pgvector
    │                    → DeepSeek V4 Flash
    │                    → optional DDGS Web Search
    └── CWCAdapter → CWC v0.1.0 public compress()
→ Workbench-owned result contracts
→ GUI
```

Workbench owns UI, integration, presentation, and API boundaries. WRA, PKRA, and CWC remain independent repositories; Workbench neither copies their source nor invokes their CLIs through subprocesses.

## Frontend

Next.js, React, TypeScript, and Tailwind CSS provide three workspaces:

- `/research/web`
- `/research/knowledge`
- `/context`

Research pages share `RunResult` presentation and REST/SSE clients. Context Lab instead uses dedicated TypeScript Context DTOs and `compressContext()`. The Frontend never imports Python, CWC, WRA, PKRA, model, or database types.

## Backend API

FastAPI provides:

- `POST /api/research/web`
- `POST /api/research/web/stream`
- `POST /api/research/knowledge`
- `POST /api/research/knowledge/stream`
- `POST /api/context/compress`

Routers receive adapters through FastAPI dependencies. They do not create model, search, database, or compression internals. Context uses REST only and has no SSE endpoint.

## Research Adapter Boundary

`WRAAdapter` maps WRA public DTOs into `RunResult`, including Answer, Trace, Metrics, and Sources available from structured search observations.

`PKRAAdapter` depends on a minimal Runner/Result Protocol and maps PKRA public results into Answer and Metrics. It measures complete runner duration with `perf_counter()`. PKRA currently provides no lossless Activity Trace or structured Source/Evidence URL boundary, so the Adapter returns `trace = []` and `sources = []`.

PKRA production composition uses only its public API:

```text
Workbench Settings
→ AgentRunnerConfig
→ create_agent_runner()
→ ProductionAgentRunner
→ PKRAAdapter
```

The request-scoped yield dependency always closes the runner.

## Context Lab Boundary

```text
Browser
→ /context
→ compressContext()
→ POST /api/context/compress
→ Context API
→ CWCAdapter
→ CWC v0.1.0 public compress()
→ Workbench Context Result
→ UI
```

Context request/result DTOs are Workbench-owned and do not reuse Research `RunResult`. `CWCAdapter` creates public CWC messages, configuration, token counter, and the selected public strategy; it invokes public `compress()` once and directly translates messages and Metrics. It does not expose CWC private partitions or implementation state.

CWC's token counter is deterministic and offline. Reported token values are estimates rather than exact provider-tokenizer counts. In CWC v0.1.0, `compression_applied=true` records that the threshold-triggered compression pipeline ran; it does not assert that messages or estimated tokens changed.

## Context Error Boundary

```text
CWC TokenBudgetError
→ Workbench ContextBudgetError
→ HTTP 422 with budget detail
```

Only the known public budget failure is translated. Unexpected CWC/Adapter exceptions retain existing server-error semantics.

## Production and Fake Isolation

`agent_engineering_workbench.app:app` resolves the real `CWCAdapter`. The local `agent_engineering_workbench.dev_server:app` module installs a deterministic Fake Context dependency override for GUI testing. The Fake path does not call CWC and does not affect a production app that is launched directly.

Fake Context Metrics are test fixtures, not benchmarks: `no_compression` reports `120 → 120`; `truncation` and `windowed` report `120 → 48`; duration is fixed at 3 ms.

## Research SSE Semantics

Web and Knowledge Research share this post-run replay contract:

```text
started
→ synchronous agent execution
→ replay available RunResult.trace
→ completed / stopped / error
```

This is not native real-time Token/Tool streaming. Context Lab does not use this contract.

## Version Scope

- v0.1.0: Workbench Shell and WRA.
- v0.2.0: PKRA Production Runner, Knowledge REST/SSE, Knowledge Frontend Workspace, and Fake Integration.
- v0.3.0: CWCAdapter, Context REST API, Context Lab, Fake Context Integration, and HTTP 422 budget boundary.

## Known Limitations

- Context token values are estimates.
- Pipeline execution does not guarantee changed Context output.
- Frontend presents a generic message for detailed HTTP 422 budget failures.
- CWC private partition/change reasons are intentionally outside the Workbench contract.
- Context Lab has no persistence or SSE.
