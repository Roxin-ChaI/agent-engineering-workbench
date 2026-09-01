**English** | [简体中文](README.zh-CN.md)

# Agent Engineering Workbench

A modular Web workbench for integrating, running, and inspecting independent AI engineering projects through a unified interface.

## v0.6.1

v0.6.1 provides six workspaces:

- Web Research uses [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent) (WRA) v0.2.0.
- Knowledge Research uses [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent) (PKRA) v0.4.0.
- Context Lab uses [`context-window-compressor`](https://github.com/Roxin-ChaI/context-window-compressor) (CWC) v0.1.0.
- GitHub Review uses [`ai-github-reviewer`](https://github.com/Roxin-ChaI/ai-github-reviewer) v0.2.0.
- Resume Optimization uses [`ai-resume-optimizer`](https://github.com/Roxin-ChaI/ai-resume-optimizer) v0.2.1.
- Prompt Experiment uses [`prompt-engineering-workbench`](https://github.com/Roxin-ChaI/prompt-engineering-workbench) v0.2.0.

All integrated projects remain independent repositories or services. The Workbench uses stable public boundaries; it neither copies their source nor invokes their CLIs through subprocesses. v0.1.0 introduced the Workbench shell and WRA, v0.2.0 added PKRA Knowledge Research, v0.3.0 added Context Lab, v0.4.0 added read-only GitHub Review, v0.4.1 added human-readable Resume provenance, v0.5.0 added controlled Prompt Experiments, and v0.6.0 adds a Prompt Library backed by Prompt Vault API v0.2.0.

## Features

- Web Research and Knowledge Research workspaces
- Final Answer, execution status, Metrics, Activity, and Sources presentation
- Context Lab message-history JSON editor and Before / After comparison
- Context compression strategy and target / maximum token-budget controls
- Estimated token reduction, compression ratio, strategy, and duration Metrics
- Read-only review of public GitHub Pull Requests with PR Overview, Summary, Findings, Test Gaps, Maintainability, Assessment, and Markdown Review
- Resume optimization with structured requirement assessments and section-aware evidence provenance
- Controlled Prompt Experiments with variant selection, deterministic success criteria, structured evaluation, and metrics
- Prompt Library List, Search, Save, Load, Update, and Delete operations backed by Prompt Vault API v0.2.0
- Collapsible navigation with a persisted expanded or compact layout
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
- `POST /api/prompts/experiment`
- `POST /api/prompts/library`
- `GET /api/prompts/library`
- `GET /api/prompts/library/search?q=...`
- `GET /api/prompts/library/{prompt_id}`
- `PUT /api/prompts/library/{prompt_id}`
- `DELETE /api/prompts/library/{prompt_id}`

The two Research workspaces offer REST and SSE boundaries. Context Lab, GitHub Review, Resume Optimization, Prompt Experiment, and Prompt Library use REST only; none exposes an SSE endpoint.

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
      → PromptExperimentAdapter
          → Prompt Engineering Workbench v0.2.0 public factory/runner
          → DeepSeek V4 Flash
          → deterministic evaluation
      → PromptVaultHttpClient
          → Prompt Vault API v0.2.0 HTTP contract
          → SQLAlchemy persistence
  → Workbench-owned result contracts
  → GUI
```

Research adapters map public agent results into the Workbench-owned `RunResult` contract. Context Lab, GitHub Review, Resume Optimization, Prompt Experiment, and Prompt Library use dedicated Workbench-owned contracts. Their integration boundaries translate public structured results; the Frontend depends only on Workbench TypeScript contracts. The Workbench does not import private project internals or access the Prompt Vault database directly.

## Dependencies

- WRA is pinned to the stable Git tag `v0.2.0`.
- PKRA with its production embedding extra is pinned to the stable Git tag `v0.4.0`.
- CWC is pinned to the stable Git tag `v0.1.0`.
- AI GitHub Reviewer is pinned to the stable Git tag `v0.2.0`.
- AI Resume Optimizer is pinned to the stable Git tag `v0.2.1`.
- Prompt Engineering Workbench is pinned to the stable Git tag `v0.2.0`.
- Normal installation does not require local WRA, PKRA, CWC, Reviewer, Resume Optimizer, or Prompt Engineering Workbench checkouts. Editable installs are optional development overrides only.
- Prompt Vault API v0.2.0 is a separate HTTP service/runtime dependency, not a Workbench Python package dependency.

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

## Prompt Experiment Workspace

Prompt Experiment is a browser workspace for one controlled experiment: one `PromptBundle`, one task, and one user-selected variant per request. It supports the six upstream public variants `baseline`, `tone_trump`, `tone_casual`, `wiki_random`, `no_tool_desc`, and `all_ablations`; it does not automatically run a six-way comparison. The GUI exposes only `max_steps` and `seed` as experiment options.

Success criteria support a required final response, an exact response, required or forbidden response substrings, and required or forbidden tool names. The current workspace provides no callable tool handlers, so required-tool criteria fail closed. All criteria passing produces `reward = 1.0` and `completed = true`; any failed criterion produces `reward = 0.0` and `completed = false`. A failed evaluation remains a valid HTTP 200 experiment result, not an HTTP error, semantic-quality score, factuality score, or LLM-as-a-Judge decision.

Production requests use the Prompt Engineering Workbench v0.2.0 public factory. Each request creates a runner, runs it exactly once, and closes it exactly once. The default model is `deepseek-v4-flash`; provider secrets remain on the Backend and are never part of the browser contract.

## Prompt Library Workspace

The `/prompts` workspace combines Prompt Experiment with a reusable Prompt Library. The Library saves `title`, prompt `content`, `wiki_rules`, and `tags`, and supports List, Search, Save, Load, Update, and Delete through Workbench-owned APIs. Loading a saved item maps `content` to Experiment `system_prompt` and `wiki_rules` to Experiment `wiki_rules`; it preserves the current task, success criteria, selected variant, `max_steps`, and `seed`.

```text
Browser
→ Workbench Prompt Library API
→ PromptVaultHttpClient
→ Prompt Vault API v0.2.0
→ SQLAlchemy persistence
```

The browser never calls Prompt Vault directly. Workbench does not import Prompt Vault's application internals or access its database. `PROMPT_VAULT_BASE_URL` and `PROMPT_VAULT_TIMEOUT_SECONDS` are Backend-only configuration; Prompt Vault database credentials never enter the Frontend.

Workbench maps Prompt Library validation failures to HTTP 422, missing items to 404, Prompt Vault transport/service failures to safe 502 responses, and unexpected internal failures to safe 500 responses. Mutations are not automatically retried. When Prompt Vault is offline, Prompt Library fails safely with HTTP 502 while Prompt Experiment remains available.

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
- prompt-engineering-workbench v0.2.0
- Prompt Vault API v0.2.0 as an independent HTTP service
- Anonymous GitHub REST GET for public Pull Requests

## Quality Baseline

- Backend: 520 tests passed
- GitHub Review focused tests: 67 passed
- Prompt Library focused Fake E2E: 12 tests passed
- Ruff: PASS
- mypy: PASS
- pip check: PASS
- Frontend ESLint: PASS
- TypeScript: PASS
- Frontend tests: 34 passed
- Next.js 16.3.1 v0.6.1 production build: PASS (TypeScript, page data, 10/10 static pages, and `/prompts` generation passed; Node v24.14.0, npm 11.9.0)
- Prompt Library manual visual verification: PASS across English/Chinese, Light/Dark, and desktop/mobile layouts

Fake GUI validation covers all three strategies, invalid JSON blocking before POST, bilingual/theme behavior, and a clean browser console. Real REST/GUI validation covers no-op compression (`45 → 45`, zero saved, `compression_applied=false`, HTTP 200), truncation (`114 → 69`, 45 estimated tokens saved, approximately 60.5% ratio, `compressed_message_count=1`, HTTP 200), TokenBudgetError → HTTP 422, and a clean browser console. Duration is measured per run and is not a fixed benchmark.

GitHub Review Fake GUI validation covers PR 42 with two Findings, PR 43 with an empty Findings state, PR 500 → HTTP 502, invalid URL → HTTP 422, empty-input blocking, English/Chinese, Light/Dark, responsive layout, and a clean browser console. Real REST/GUI validation against public PR `openai/openai-python#3357` passed with structured metadata, two Findings, Assessment, Test Gaps, Maintainability, Markdown Review, a single HTTP 200 business POST, a clean console, and no GitHub writes.

Resume Provenance Real GUI validation passed against the production app with one HTTP 200 request: human-readable requirement descriptions, importance/status, section-aware evidence excerpts, hidden machine IDs, English/Chinese, Light/Dark, responsive layout, and a clean console.

Prompt Workspace deterministic Fake E2E covers success, failed criteria, the required-tools guard, variant and request fidelity, input validation, production isolation, and zero DeepSeek calls through pytest/TestClient plus local browser verification. Real Prompt Workspace E2E passed in production mode with `deepseek-v4-flash`: one Prompt POST returned HTTP 200, reward 1.0, completed true, all criteria passed, zero tool calls, a clean console, protected provider secrets, correct request-scoped lifecycle, and verified bilingual/theme/responsive behavior.

Prompt Library deterministic Fake E2E covers initial list, Save, Search, Load fidelity, Update, explicit rule clearing, Delete, upstream error isolation, mutation failure, request fidelity, Prompt Experiment regression, production isolation, protected secrets, and no automatic retry. Real Prompt Library E2E passed through a real Prompt Vault API v0.2.0 service, real Workbench Backend, real Frontend, SQLAlchemy, and temporary SQLite. It verified Save/Search/Load/Update/Delete, explicit `wiki_rules` clearing, safe HTTP 502 isolation while Prompt Vault was offline, persistence after restart, browser secret boundaries, no mutation retry, cleanup, and a clean console.

## Known Limitations

- Context token values are estimates, not exact tokenizer counts.
- `compression_applied=true` indicates pipeline execution, not necessarily changed output.
- Context HTTP 422 responses contain useful budget detail, but the current Frontend displays only `Unable to compress this context.`
- CWC private partition/change reasons are not exposed to Workbench.
- Context Lab currently has no persistence or SSE.
- PKRA structured Sources/Evidence and Activity Trace are not currently mapped.
- Research SSE replays available events after synchronous execution; native real-time streaming is unavailable.
- Prompt Experiment runs one task and one selected variant per request; it has no automatic comparison matrix.
- Prompt Library has no pagination, authentication/multi-user workflow, prompt history/version history, experiment-result persistence, or template-variable system.
- Prompt Experiment has no arbitrary callable tools; required-tool criteria fail closed.
- Prompt evaluation is deterministic and binary, with no partial credit or semantic LLM judge.

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Local development](docs/local-development.md)
