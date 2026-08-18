# Local Development

## Prerequisites

- Python 3.12
- Node.js and npm
- The Workbench `.venv`
- PostgreSQL with pgvector and pre-indexed PKRA data for real Knowledge Research

## Standard Installation

The Backend package metadata pins both integrations to stable Git tags:

- `web-research-agent` v0.2.0
- `production-knowledge-research-agent[e2e]` v0.4.0

The PKRA extra supplies the SentenceTransformer runtime required by its Production Runner. Install the Backend and development tools from the project root:

```sh
.venv/bin/python -m pip install -e './backend[dev]'
```

Normal installation does not require local WRA or PKRA checkouts. Formal dependencies use fixed Git tags, not local paths or floating branches.

## Optional Editable Overrides

Use editable overrides only when developing Workbench and an agent repository together:

```sh
.venv/bin/python -m pip install -e '<path-to-wra>'
.venv/bin/python -m pip install -e '<path-to-pkra>[e2e]'
```

These commands make the current environment use local source. They are not formal dependency declarations and must not be added to `pyproject.toml`.

## Fake GUI Run

Start the local fake Backend from the project root:

```sh
.venv/bin/python -m agent_engineering_workbench.dev_server
```

Start the Frontend in another shell:

```sh
cd frontend && npm run dev
```

The dev server overrides both research dependencies with deterministic fake adapters. It does not create WRA/PKRA production objects and does not require PostgreSQL, an API key, DeepSeek, or DDGS.

## Real Application

Set configuration in the shell; never commit secrets:

```sh
export MODEL_PROVIDER=deepseek
export MODEL_NAME=deepseek-v4-flash
export DEEPSEEK_API_KEY='<your-deepseek-api-key>'
export PKRA_DATABASE_URL='postgresql+psycopg://<user>:<password>@<host>:<port>/<database>'
export PKRA_ENABLE_WEB_SEARCH=true
.venv/bin/uvicorn agent_engineering_workbench.app:app --host 127.0.0.1 --port 8000
```

`PKRA_DATABASE_URL` must point to PostgreSQL/pgvector reachable from the Workbench Backend and containing pre-indexed data. Set `PKRA_ENABLE_WEB_SEARCH=false` for knowledge-only research or `true` to enable PKRA's DDGS Web Search.

Start the Frontend separately:

```sh
cd frontend && npm run dev
```

Open either workspace:

- `http://localhost:3000/research/web`
- `http://localhost:3000/research/knowledge`

Use `agent_engineering_workbench.app:app` for real WRA/PKRA execution. Do not use `dev_server` for a real E2E because its dependency overrides intentionally return fake results. Real execution may call DeepSeek and DDGS and may incur API costs.

## Current PKRA Contract Limits

PKRA currently returns Answer and Metrics to Workbench, but no mapped Activity Trace or structured Sources/Evidence. Empty `trace` and `sources` are expected contract limitations. Knowledge SSE uses post-run replay semantics and is not native real-time Token/Tool streaming.
