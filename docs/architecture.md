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
    ├── CWCAdapter → CWC v0.1.0 public compress()
    ├── GitHubReviewerAdapter
                         → AI GitHub Reviewer v0.2.0 public runner
                         → anonymous GitHub REST GET
                         → DeepSeek V4 Flash
    └── ResumeOptimizerAdapter
                         → AI Resume Optimizer v0.2.1 public runner
                         → DeepSeek V4 Flash
→ Workbench-owned result contracts
→ GUI
```

Workbench owns UI, integration, presentation, and API boundaries. WRA, PKRA, CWC, AI GitHub Reviewer, and AI Resume Optimizer remain independent repositories; Workbench neither copies their source nor invokes their CLIs through subprocesses.

## Frontend

Next.js, React, TypeScript, and Tailwind CSS provide five workspaces:

- `/research/web`
- `/research/knowledge`
- `/context`
- `/github`
- `/resume`

Research pages share `RunResult` presentation and REST/SSE clients. Context Lab, GitHub Review, and Resume Optimization use dedicated Workbench-owned TypeScript contracts and REST clients. The Frontend never imports Python, CWC, WRA, PKRA, Reviewer, Resume Optimizer, model, or database types.

## Backend API

FastAPI provides:

- `POST /api/research/web`
- `POST /api/research/web/stream`
- `POST /api/research/knowledge`
- `POST /api/research/knowledge/stream`
- `POST /api/context/compress`
- `POST /api/github/review`
- `POST /api/resume/optimize`

Routers receive adapters through FastAPI dependencies. They do not create model, search, database, compression, Reviewer, or Resume Optimizer internals. Context, GitHub Review, and Resume Optimization use REST only and have no SSE endpoints.

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

## GitHub Review Boundary

```text
Browser
→ /github
→ reviewPullRequest()
→ POST /api/github/review
→ GitHubReviewerAdapter
→ AI GitHub Reviewer v0.2.0 public create_reviewer()/runner
→ anonymous GitHub REST GET
→ DeepSeek V4 Flash
→ Workbench-owned GitHub Review Result
→ UI
```

The request contains a public Pull Request URL. The structured result contains PR metadata, Summary, Findings, Test Gaps, Maintainability, Assessment, and Markdown Review. A Finding contains severity, file path, location, issue, evidence, and recommendation. The Adapter translates the Reviewer's public DTOs without importing private modules or invoking its CLI.

The request-scoped dependency creates the public Reviewer runner and closes it in `finally`. Invalid PR URLs are rejected with HTTP 422; categorized upstream/review protocol failures become HTTP 502; unknown internal failures retain a safe HTTP 500 boundary.

GitHub Review is read-only: public PRs only, anonymous GitHub REST GET, no GitHub token, no comments, no submitted review, no approve/request-changes action, no merge/close, no repository mutation, and no execution of PR code. Assessment is display data, not a GitHub action.

## Resume Optimization Boundary

```text
Browser
→ /resume
→ optimizeResume()
→ POST /api/resume/optimize
→ ResumeOptimizerAdapter
→ AI Resume Optimizer v0.2.1 public create_resume_optimizer()/runner
→ Workbench-owned Resume Result
→ provenance-aware UI
```

The multipart request contains a PDF or DOCX resume plus job-description text. The request-scoped dependency owns and closes the public runner, while the route guarantees temporary-file cleanup. The Adapter translates the public structured result without parsing CLI exports or importing private modules.

Requirement and evidence provenance is additive: legacy machine IDs remain in the contract for deterministic association, while human-readable requirement references and ordered evidence records are mapped directly. Evidence excerpts originate from parsed source blocks and preserve source order; the normal UI does not expose machine IDs.

## Production and Fake Isolation

`agent_engineering_workbench.app:app` resolves all real adapters. Only `agent_engineering_workbench.dev_server:app` installs deterministic Fake Web, Knowledge, Context, GitHub Review, and Resume dependency overrides. Fake GitHub Review supports PR 42 (two Findings), PR 43 (empty Findings), PR 500 (HTTP 502), and invalid URL (HTTP 422). The production app never falls back to a Fake adapter when configuration or an upstream call fails.

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
- v0.4.0: AI GitHub Reviewer v0.2.0 Adapter/API/Frontend integration, deterministic Fake scenarios, and read-only GitHub Review workspace.
- v0.4.1: AI Resume Optimizer v0.2.1 provenance contracts, Adapter mapping, and human-readable Resume workspace evidence.

## Known Limitations

- Context token values are estimates.
- Pipeline execution does not guarantee changed Context output.
- Frontend presents a generic message for detailed HTTP 422 budget failures.
- CWC private partition/change reasons are intentionally outside the Workbench contract.
- Context Lab has no persistence or SSE.
