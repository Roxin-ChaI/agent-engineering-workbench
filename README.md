**English** | [简体中文](README.zh-CN.md)

# Agent Engineering Workbench

A modular Web workbench for integrating, running, and inspecting independent AI Agent engineering projects through a unified interface.

## v0.2.0

v0.2.0 provides two production research workspaces:

- Web Research uses [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent) (WRA) v0.2.0.
- Knowledge Research uses [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent) (PKRA) v0.4.0.

Both agents remain independent repositories. The Workbench integrates their public Python APIs through adapters; it neither copies their source nor invokes their CLIs through subprocesses. v0.1.0 introduced the Workbench shell and WRA integration, while v0.2.0 adds PKRA Knowledge Research.

## Features

- Web Research and Knowledge Research workspaces
- Final Answer and execution status display
- Iteration, tool-call, and execution-duration Metrics
- WRA Agent Activity / Trace replay and structured Sources
- Graceful empty Activity and Sources / Evidence states for PKRA
- English and Chinese UI
- Dark and Light themes with persisted preferences
- Fake local integration mode and production agent integrations

## Routes and API

Frontend routes:

- `/`
- `/research/web`
- `/research/knowledge`
- `/context`, `/prompts`, `/resume`, and `/github`

Backend research endpoints:

- `POST /api/research/web`
- `POST /api/research/web/stream`
- `POST /api/research/knowledge`
- `POST /api/research/knowledge/stream`

## Architecture

```text
Browser
  → Next.js Workbench
  → FastAPI
      → WRAAdapter
          → WRA v0.2.0
      → PKRAAdapter
          → PKRA v0.4.0 ProductionAgentRunner
              → PostgreSQL / pgvector
              → DeepSeek V4 Flash
              → optional DDGS Web Search
  → RunResult
  → GUI
```

`WRAAdapter` and `PKRAAdapter` map public agent results into the Workbench-owned `RunResult` contract. The adapter boundary keeps Workbench business logic independent of agent internals. PKRA is composed through its public Production Runner API; the Workbench does not import PKRA private runtime modules.

## Dependencies

- WRA is pinned to the stable Git tag `v0.2.0`.
- PKRA with its production embedding extra is pinned to the stable Git tag `v0.4.0`.
- A normal Workbench installation does not require a local PKRA checkout. Editable installs are optional development overrides only.

## Knowledge Research Behavior

Users submit indexed-knowledge questions through `/research/knowledge`. PKRA returns the Answer and Metrics through the standard `RunResult` contract. Its current public result contract does not expose a lossless activity trace or structured source/evidence URLs for Workbench mapping, so successful runs currently contain:

```text
trace = []
sources = []
```

These empty fields are known contract limitations, not execution failures.

## SSE Semantics

Both research streams use the same post-run replay protocol:

```text
started
→ synchronous agent execution
→ replay available trace
→ completed / stopped / error
```

Neither endpoint provides native real-time token/tool streaming. Because PKRA currently supplies no mapped trace, a typical successful Knowledge Research stream is `started → completed`.

## Tech Stack

- Python 3.12 and FastAPI
- Next.js, React, TypeScript, and Tailwind CSS
- DeepSeek V4 Flash (`deepseek-v4-flash`)
- PostgreSQL / pgvector and optional DDGS for PKRA
- web-research-agent v0.2.0
- production-knowledge-research-agent v0.4.0

## Quality Baseline

- Backend: 126 tests passed
- Ruff: PASS
- mypy strict: PASS
- pip check: PASS
- Frontend ESLint: PASS
- TypeScript: PASS

Real validation completed for Fake Knowledge GUI E2E, PKRA Production Runner knowledge-only and web-enabled flows, Workbench Real Knowledge REST, and Workbench Real Knowledge GUI. Execution duration varies per run and is reported as a measured metric rather than a fixed baseline.

## Known Limitations

- PKRA structured sources/evidence are not currently mapped into Workbench.
- PKRA activity trace is not currently mapped into Workbench.
- SSE replays available events after synchronous execution; native real-time token/tool streaming is not yet available.

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Local development](docs/local-development.md)
