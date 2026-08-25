**English** | [简体中文](README.zh-CN.md)

# Agent Engineering Workbench

A modular Web workbench for integrating, running, and inspecting independent AI engineering projects through a unified interface.

## v0.4.1

v0.4.1 provides five workspaces:

- Web Research uses [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent) (WRA) v0.2.0.
- Knowledge Research uses [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent) (PKRA) v0.4.0.
- Context Lab uses [`context-window-compressor`](https://github.com/Roxin-ChaI/context-window-compressor) (CWC) v0.1.0.
- GitHub Review uses [`ai-github-reviewer`](https://github.com/Roxin-ChaI/ai-github-reviewer) v0.2.0.
- Resume Optimization uses [`ai-resume-optimizer`](https://github.com/Roxin-ChaI/ai-resume-optimizer) v0.2.1.

All five projects remain independent repositories. The Workbench integrates their public Python APIs through adapter boundaries; it neither copies their source nor invokes their CLIs through subprocesses. v0.1.0 introduced the Workbench shell and WRA, v0.2.0 added PKRA Knowledge Research, v0.3.0 added Context Lab, v0.4.0 added read-only GitHub Review, and v0.4.1 adds human-readable Resume provenance.

## Features

- Web Research and Knowledge Research workspaces
- Final Answer, execution status, Metrics, Activity, and Sources presentation
- Context Lab message-history JSON editor and Before / After comparison
- Context compression strategy and target / maximum token-budget controls
- Estimated token reduction, compression ratio, strategy, and duration Metrics
- Read-only review of public GitHub Pull Requests with PR Overview, Summary, Findings, Test Gaps, Maintainability, Assessment, and Markdown Review
- Resume optimization with structured requirement assessments and section-aware evidence provenance
- English and Chinese UI
- Dark and Light themes with persisted preferences
- Fake local integration mode and production integrations

## Routes and API

Frontend routes:

- `/`
- `/research/web`
- `/research/knowledge`
- `/context`
- `/github`
- `/resume`
- `/prompts`

Backend endpoints:

- `POST /api/research/web`
- `POST /api/research/web/stream`
- `POST /api/research/knowledge`
- `POST /api/research/knowledge/stream`
- `POST /api/context/compress`
- `POST /api/github/review`
- `POST /api/resume/optimize`

The two Research workspaces offer REST and SSE boundaries. Context Lab, GitHub Review, and Resume Optimization use REST only; none exposes an SSE endpoint.

## Architecture

```text
Browser
  → Next.js Workbench
  → FastAPI
      → WRAAdapter → WRA v0.2.0
      → PKRAAdapter → PKRA v0.4.0 ProductionAgentRunner
          → PostgreSQL / pgvector
          → DeepSeek V4 Flash
          → optional DDGS Web Search
      → CWCAdapter → CWC v0.1.0 public compress()
      → GitHubReviewerAdapter
          → AI GitHub Reviewer v0.2.0 public runner
          → anonymous GitHub REST GET
          → DeepSeek V4 Flash
      → ResumeOptimizerAdapter
          → AI Resume Optimizer v0.2.1 public runner
          → DeepSeek V4 Flash
  → Workbench-owned result contracts
  → GUI
```

Research adapters map public agent results into the Workbench-owned `RunResult` contract. Context Lab, GitHub Review, and Resume Optimization use dedicated Workbench-owned contracts. Their adapters translate public structured results; the Frontend depends only on Workbench TypeScript contracts. The Workbench does not import private project internals.

## Dependencies

- WRA is pinned to the stable Git tag `v0.2.0`.
- PKRA with its production embedding extra is pinned to the stable Git tag `v0.4.0`.
- CWC is pinned to the stable Git tag `v0.1.0`.
- AI GitHub Reviewer is pinned to the stable Git tag `v0.2.0`.
- AI Resume Optimizer is pinned to the stable Git tag `v0.2.1`.
- Normal installation does not require local WRA, PKRA, CWC, Reviewer, or Resume Optimizer checkouts. Editable installs are optional development overrides only.

## Context Lab

Context Lab accepts:

- a message-history JSON array;
- `no_compression`, `truncation`, or `windowed`;
- a target token budget; and
- a maximum token budget.

It displays Original Messages, Compressed Messages, Estimated Original Tokens, Estimated Compressed Tokens, Estimated Tokens Saved, Compression Ratio, Strategy, and Duration. The API contract also reports whether the pipeline ran and how many input messages were compressed or preserved.

Token values are deterministic estimates from CWC's offline counter, not exact provider-tokenizer counts. CWC runs locally, requires no API key, and has no network dependency. The adapter calls CWC's public `compress()` API.

In CWC v0.1.0, `compression_applied=true` means the compression threshold was reached and the compression pipeline executed. It does not guarantee that the final messages or estimated token count changed.

An unsatisfiable hard budget—for example, protected fixed/recent messages exceeding the maximum—follows this boundary:

```text
CWC TokenBudgetError
→ Workbench Context domain error
→ HTTP 422
```

## GitHub Review

GitHub Review accepts a public Pull Request URL and returns a Workbench-owned structured result containing PR Overview, Summary, Findings, Test Gaps, Maintainability, Assessment, and Markdown Review. Each Finding contains severity, file path, location, issue, evidence, and recommendation.

```text
Browser
→ POST /api/github/review
→ GitHubReviewerAdapter
→ AI GitHub Reviewer v0.2.0 public runner
→ anonymous GitHub REST GET
→ DeepSeek V4 Flash
→ structured Workbench result
→ UI
```

The integration is strictly read-only: public PRs only, anonymous GitHub REST GET requests, no GitHub token, no comments, no submitted reviews, no approve/request-changes action, no merge/close, no repository mutation, and no execution of PR code. The UI's Assessment is model output for display, not a GitHub action.

The endpoint uses REST only. Invalid PR URLs return HTTP 422, upstream/review protocol failures return HTTP 502, and unknown internal failures return a safe HTTP 500 response.

## Resume Provenance Integration

Resume Optimization displays structured job requirement references and the resume evidence supporting each assessment. Requirement cards use the human-readable description, importance, and match status. Evidence cards prefer section titles and show the corresponding source excerpt; internal requirement and source-block IDs remain available for deterministic association but are hidden from the normal UI.

The provenance comes from AI Resume Optimizer v0.2.1. Evidence is mapped deterministically from the parsed resume `SourceBlock` data while preserving source order. It is not a generated explanation, an inferred source, fuzzy matching, or content reconstructed from the optimized resume. Legacy responses without provenance remain supported through a non-breaking fallback.

## Research Behavior and SSE Semantics

PKRA returns Answer and Metrics through `RunResult`, but its current public result has no lossless activity trace or structured source/evidence URLs. Successful Knowledge runs therefore currently contain `trace = []` and `sources = []`; these are known contract limitations, not execution failures.

Both Research streams use the same post-run replay protocol:

```text
started
→ synchronous agent execution
→ replay available trace
→ completed / stopped / error
```

Neither endpoint provides native real-time token/tool streaming.

## Tech Stack

- Python 3.12 and FastAPI
- Next.js, React, TypeScript, and Tailwind CSS
- DeepSeek V4 Flash (`deepseek-v4-flash`)
- PostgreSQL / pgvector and optional DDGS for PKRA
- web-research-agent v0.2.0
- production-knowledge-research-agent v0.4.0
- context-window-compressor v0.1.0
- ai-github-reviewer v0.2.0
- ai-resume-optimizer v0.2.1
- Anonymous GitHub REST GET for public Pull Requests

## Quality Baseline

- Backend: 311 tests passed
- Ruff: PASS
- mypy: PASS
- pip check: PASS
- Frontend ESLint: PASS
- TypeScript: PASS
- Next.js 16.3.1 production build: PASS (static page generation: PASS; `/resume` included)

Fake GUI validation covers all three strategies, invalid JSON blocking before POST, bilingual/theme behavior, and a clean browser console. Real REST/GUI validation covers no-op compression (`45 → 45`, zero saved, `compression_applied=false`, HTTP 200), truncation (`114 → 69`, 45 estimated tokens saved, approximately 60.5% ratio, `compressed_message_count=1`, HTTP 200), TokenBudgetError → HTTP 422, and a clean browser console. Duration is measured per run and is not a fixed benchmark.

GitHub Review Fake GUI validation covers PR 42 with two Findings, PR 43 with an empty Findings state, PR 500 → HTTP 502, invalid URL → HTTP 422, empty-input blocking, English/Chinese, Light/Dark, responsive layout, and a clean browser console. Real REST/GUI validation against public PR `openai/openai-python#3357` passed with structured metadata, two Findings, Assessment, Test Gaps, Maintainability, Markdown Review, a single HTTP 200 business POST, a clean console, and no GitHub writes.

Resume Provenance Real GUI validation passed against the production app with one HTTP 200 request: human-readable requirement descriptions, importance/status, section-aware evidence excerpts, hidden machine IDs, English/Chinese, Light/Dark, responsive layout, and a clean console.

## Known Limitations

- Context token values are estimates, not exact tokenizer counts.
- `compression_applied=true` indicates pipeline execution, not necessarily changed output.
- Context HTTP 422 responses contain useful budget detail, but the current Frontend displays only `Unable to compress this context.`
- CWC private partition/change reasons are not exposed to Workbench.
- Context Lab currently has no persistence or SSE.
- PKRA structured Sources/Evidence and Activity Trace are not currently mapped.
- Research SSE replays available events after synchronous execution; native real-time streaming is unavailable.

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Local development](docs/local-development.md)
