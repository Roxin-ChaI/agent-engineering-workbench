# Local Development

## Prerequisites

- Python 3.12
- Node.js and npm
- A separate local WRA repository
- The Workbench `.venv`
- WRA installed into the Workbench environment in editable mode:

  ```sh
  .venv/bin/python -m pip install -e /Users/mac/Projects/web-research-agent
  ```

The absolute path above is only for the current local development setup. It is not a deployable dependency strategy.

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
