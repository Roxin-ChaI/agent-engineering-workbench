# Local Development

## Prerequisites

- Python 3.12
- Node.js and npm
- The Workbench `.venv`
- PostgreSQL with pgvector and pre-indexed PKRA data only for real Knowledge Research

Context Lab itself requires no API key, database, Redis, DDGS, model provider, or external network call.
Real GitHub Review requires a DeepSeek API key but no GitHub token.

## Standard Installation

Backend package metadata pins all integrations to stable Git tags:

- `web-research-agent` v0.2.0
- `production-knowledge-research-agent[e2e]` v0.4.0
- `context-window-compressor` v0.1.0
- `ai-github-reviewer` v0.2.0

Install Backend and development tools from the project root:

```sh
.venv/bin/python -m pip install -e './backend[dev]'
```

Normal installation does not require local WRA, PKRA, CWC, or AI GitHub Reviewer checkouts. Formal dependencies use fixed Git tags, not local paths or floating branches.

## Optional Editable Overrides

Use editable overrides only when developing Workbench and an integrated project together:

```sh
.venv/bin/python -m pip install -e '<path-to-wra>'
.venv/bin/python -m pip install -e '<path-to-pkra>[e2e]'
.venv/bin/python -m pip install -e '<path-to-cwc>'
.venv/bin/python -m pip install -e '<path-to-ai-github-reviewer>'
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

Open `http://localhost:3000/context` or `http://localhost:3000/github`.

The dev server provides deterministic Fake Web, Knowledge, Context, and GitHub Review adapters. Fake Context results are suitable for Before / After UI checks without executing CWC:

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

## Validation Notes

The Context Lab Fake GUI, real no-op compression, real `114 → 69` truncation, and TokenBudgetError → HTTP 422 paths have been manually verified. Execution duration varies per run and is not a fixed baseline.

Fake GitHub Review GUI scenarios for PR 42, PR 43, PR 500, invalid URL, and empty input have passed along with bilingual UI, themes, responsive layout, and a clean console. Real REST/GUI validation against public PR `openai/openai-python#3357` passed with structured metadata, two Findings, Assessment, Test Gaps, Maintainability, Markdown Review, a single HTTP 200 business POST, a clean console, and no GitHub writes.

The v0.3.0 release baseline includes a successful Next.js production build.
The v0.4.0 Next.js 16.3.1 production build passed, including TypeScript, static page generation, and the `/github` route.
Run `cd frontend && npm run build` to repeat this local verification.
