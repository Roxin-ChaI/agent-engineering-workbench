# Local Development

## Prerequisites

- Python 3.12
- Node.js and npm
- The Workbench `.venv`

## Standard Installation

The Backend package metadata pins `web-research-agent` to the GitHub tag `v0.2.0` and `production-knowledge-research-agent[e2e]` to `v0.4.0`. The PKRA extra supplies the SentenceTransformer runtime required by its production runner. A normal Backend installation resolves both agents from their fixed Git tags:

```sh
.venv/bin/python -m pip install -e './backend[dev]'
```

The formal dependencies do not use a local absolute path or a floating branch. A normal Workbench installation does not require a local PKRA repository.

## Local WRA Development Override

When developing WRA and Workbench together, install the separate local WRA repository into the Workbench environment in editable mode:

```sh
.venv/bin/python -m pip install -e /Users/mac/Projects/web-research-agent
```

This is only a local development override: the current environment uses the local WRA source directly. It is not the formal project dependency, and the absolute path must not be added to `pyproject.toml`.

## Local PKRA Development Override

When developing PKRA and Workbench together, the fixed Git dependency may be replaced in the current environment with an editable local checkout:

```sh
pip install -e '<path-to-pkra>[e2e]'
```

This optional override makes the current environment use local PKRA source. It is not the formal project dependency and must not be added to `pyproject.toml`.

## Fake GUI Run

Start the fake Backend from the project root:

```sh
.venv/bin/python -m agent_engineering_workbench.dev_server
```

Start the Frontend in another shell:

```sh
cd frontend && npm run dev
```

Fake mode uses deterministic local results and does not access DeepSeek or DDGS.

## Real WRA Run

Run these commands manually. Do not commit an API key:

```sh
export MODEL_PROVIDER=deepseek
export MODEL_NAME=deepseek-v4-flash
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
.venv/bin/uvicorn agent_engineering_workbench.app:app --host 127.0.0.1 --port 8000
```

Start the Frontend in another shell:

```sh
cd frontend && npm run dev
```

Open `http://localhost:3000/research/web`.

Real WRA calls DeepSeek and DDGS and may incur API costs. A real test must be run manually by the user, and the API key must never be written to Git.
