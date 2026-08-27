# Local Development

## Prerequisites

- Python 3.12
- Node.js and npm
- The Workbench `.venv`
- PostgreSQL with pgvector and pre-indexed PKRA data only for real Knowledge Research

Context Lab itself requires no API key, database, Redis, DDGS, model provider, or external network call.
Real GitHub Review requires a DeepSeek API key but no GitHub token. Real Resume Optimization and Real Prompt Experiment also require a DeepSeek API key.

## Standard Installation

Backend package metadata pins all integrations to stable Git tags:

- `web-research-agent` v0.2.0
- `production-knowledge-research-agent[e2e]` v0.4.0
- `context-window-compressor` v0.1.0
- `ai-github-reviewer` v0.2.0
- `ai-resume-optimizer` v0.2.1
- `prompt-engineering-workbench` v0.2.0

Install Backend and development tools from the project root:

```sh
.venv/bin/python -m pip install -e './backend[dev]'
```

Normal installation does not require local WRA, PKRA, CWC, AI GitHub Reviewer, AI Resume Optimizer, or Prompt Engineering Workbench checkouts. Formal dependencies use fixed Git tags, not local paths or floating branches.

## Optional Editable Overrides

Use editable overrides only when developing Workbench and an integrated project together:

```sh
.venv/bin/python -m pip install -e '<path-to-wra>'
.venv/bin/python -m pip install -e '<path-to-pkra>[e2e]'
.venv/bin/python -m pip install -e '<path-to-cwc>'
.venv/bin/python -m pip install -e '<path-to-ai-github-reviewer>'
.venv/bin/python -m pip install -e '<path-to-ai-resume-optimizer>'
.venv/bin/python -m pip install -e '<path-to-prompt-engineering-workbench>'
```

These commands make the current environment use local source. They are not formal dependency declarations and must not be added to `pyproject.toml`.

## Fake GUI Run

From the Backend directory, start the development app explicitly:

```sh
cd backend
../.venv/bin/python -m uvicorn \
  agent_engineering_workbench.dev_server:app \
  --host 127.0.0.1 \
  --port 8000
```

Start the Frontend in another shell:

```sh
cd frontend
npm run dev
```

Open `http://localhost:3000/context`, `http://localhost:3000/github`, `http://localhost:3000/resume`, or `http://localhost:3000/prompts`.

The dev server provides deterministic Fake Web, Knowledge, Context, GitHub Review, Resume, and Prompt adapters. Fake Context results are suitable for Before / After UI checks without executing CWC:

- `no_compression`: `120 → 120`
- `truncation`: `120 → 48`
- `windowed`: `120 → 48`
- duration: 3 ms

These values are fixtures, not CWC performance or compression benchmarks.

Fake GitHub Review is also deterministic and never calls GitHub or DeepSeek:

- PR 42: success with two Findings
- PR 43: success with an empty Findings state
- PR 500: HTTP 502
- invalid PR URL: HTTP 422

These overrides exist only in `dev_server:app`. The production app never falls back to Fake behavior.

Fake Prompt Experiment uses the same `POST /api/prompts/experiment` route and frontend contract as production. It deterministically covers successful and failed criteria, required-tool guarding, variant/request fidelity, and input validation without requiring `DEEPSEEK_API_KEY` or calling DeepSeek.

## Real Context Lab

Start the production app directly rather than importing `dev_server`:

```sh
cd backend
../.venv/bin/python -m uvicorn \
  agent_engineering_workbench.app:app \
  --host 127.0.0.1 \
  --port 8000
```

Then start the Frontend and open `http://localhost:3000/context`:

```sh
cd frontend
npm run dev
```

This path uses the real `CWCAdapter` and CWC v0.1.0 public `compress()` API. It remains local/offline and does not require an API key, PostgreSQL, Redis, DDGS, or a model provider. Token values are estimates, not exact tokenizer counts.

An impossible maximum budget returns HTTP 422. The response includes budget detail, while the current Frontend displays the stable generic message `Unable to compress this context.`

## Real Research Application

Set Research configuration in the shell; never commit secrets:

```sh
export MODEL_PROVIDER=deepseek
export MODEL_NAME=deepseek-v4-flash
export DEEPSEEK_API_KEY='<your-deepseek-api-key>'
export PKRA_DATABASE_URL='postgresql+psycopg://<user>:<password>@<host>:<port>/<database>'
export PKRA_ENABLE_WEB_SEARCH=true
cd backend
../.venv/bin/python -m uvicorn \
  agent_engineering_workbench.app:app \
  --host 127.0.0.1 \
  --port 8000
```

`PKRA_DATABASE_URL` must point to reachable PostgreSQL/pgvector with pre-indexed data. Set `PKRA_ENABLE_WEB_SEARCH=false` for knowledge-only research or `true` for optional DDGS Web Search.

Open either Research workspace after starting the Frontend:

- `http://localhost:3000/research/web`
- `http://localhost:3000/research/knowledge`

Real Research may call DeepSeek and DDGS and may incur API costs. Research SSE uses post-run Trace replay rather than native real-time Token/Tool streaming.

## Real GitHub Review

Set the DeepSeek key in the shell and start the production app directly:

```sh
export DEEPSEEK_API_KEY='<your-deepseek-api-key>'
cd backend
../.venv/bin/python -m uvicorn \
  agent_engineering_workbench.app:app \
  --host 127.0.0.1 \
  --port 8000
```

Start the Frontend, open `http://localhost:3000/github`, and submit a public GitHub Pull Request URL. No `GITHUB_TOKEN` is required or supported. The integration uses anonymous GitHub REST GET only and never comments, submits a review, approves, requests changes, merges, closes, mutates a repository, or executes PR code. Real Review calls DeepSeek and may incur API costs; never commit the key.

## Real Resume Optimization

Set `DEEPSEEK_API_KEY`, start `agent_engineering_workbench.app:app`, and open `http://localhost:3000/resume`. Upload a PDF or DOCX resume and provide job-description text. The production chain uses AI Resume Optimizer v0.2.1's public runner; it does not invoke the CLI or parse exported files.

Requirement and evidence provenance is deterministic. The UI displays requirement description, importance, status, section-aware evidence excerpts, and hides internal requirement/source-block IDs. Resume contents are sent to the configured model for the request; the Workbench removes its temporary upload when the request ends and does not persist it.

## Real Prompt Experiment

Set `DEEPSEEK_API_KEY`, start `agent_engineering_workbench.app:app`, and open `http://localhost:3000/prompts`. Submit one prompt bundle, one task, one selected variant, deterministic success criteria, and the GUI options `max_steps` and `seed`.

Production uses Prompt Engineering Workbench v0.2.0's public factory with default model `deepseek-v4-flash`. Each HTTP request creates a request-scoped runner, runs it once, and closes it once. The browser never receives the API key. The workspace has no callable tool handlers, so required-tool criteria fail closed; failed deterministic evaluation remains an HTTP 200 result with reward 0.0 and `completed=false`.

## Validation Notes

The Context Lab Fake GUI, real no-op compression, real `114 → 69` truncation, and TokenBudgetError → HTTP 422 paths have been manually verified. Execution duration varies per run and is not a fixed baseline.

Fake GitHub Review GUI scenarios for PR 42, PR 43, PR 500, invalid URL, and empty input have passed along with bilingual UI, themes, responsive layout, and a clean console. Real REST/GUI validation against public PR `openai/openai-python#3357` passed with structured metadata, two Findings, Assessment, Test Gaps, Maintainability, Markdown Review, a single HTTP 200 business POST, a clean console, and no GitHub writes.

Real Resume GUI validation passed through the production app with one HTTP 200 request. Requirement descriptions, importance/status, section-aware evidence excerpts, hidden machine IDs, bilingual UI, Light/Dark themes, responsive layout, and a clean console were verified.

Prompt Workspace Fake E2E passed with deterministic pytest/TestClient coverage and zero DeepSeek calls. Real Prompt Workspace E2E passed in production mode with `deepseek-v4-flash`: one Prompt POST, HTTP 200, reward 1.0, completed true, all criteria passed, zero tool calls, protected secrets, correct lifecycle, a clean console, and verified bilingual/theme/responsive behavior. Do not repeat the real run during routine local validation.

The v0.3.0 release baseline includes a successful Next.js production build.
The v0.4.0 Next.js 16.3.1 production build passed, including TypeScript, static page generation, and the `/github` route.
The v0.4.1 Next.js 16.3.1 production build passed, including TypeScript, static page generation, and the `/resume` route.
The v0.5.0 production build must be verified manually before tagging if the Codex sandbox blocks Turbopack with `EPERM`.
Run `cd frontend && npm run build` to repeat this local verification.
