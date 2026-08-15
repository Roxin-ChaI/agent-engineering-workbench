**English** | [简体中文](README.zh-CN.md)

# Agent Engineering Workbench

A modular Web workbench for integrating, running, and inspecting independent AI Agent engineering projects through a unified interface.

## v0.1.0

The first release integrates one independent project: [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent) v0.2.0. It provides the Workbench shell and a Web Research workspace without copying or reimplementing the WRA runtime, model integration, or search logic.

## Features

- Web Research workflow
- Final Answer display
- Agent Activity / Trace replay
- Iteration, tool-call, and WRA execution-duration Metrics
- Structured Sources
- English and Chinese UI
- Dark and Light themes with persisted preferences
- Fake local integration mode and production WRA integration

Modules outside the v0.1.0 scope remain placeholders and are not presented as completed integrations.

## Architecture

```text
Browser
→ Next.js
→ FastAPI
→ WRAAdapter
→ WebResearchAgent
→ DeepSeek V4 Flash / DDGS
→ RunResult
→ SSE
→ GUI
```

WRA remains an independent repository and is pinned to v0.2.0 as a reproducible Git dependency. The Workbench does not copy WRA source code. `WRAAdapter` maps WRA public result DTOs into the Workbench-owned `RunResult` contract, while the adapter contract provides an extension boundary for future project integrations.

## SSE Semantics

The current WRA `run()` API is synchronous. In v0.1.0, `/api/research/web/stream` uses SSE to:

1. emit `started`;
2. execute WRA;
3. replay the trace in order after WRA completes; and
4. emit one terminal `completed`, `stopped`, or `error` event.

Native real-time agent/tool streaming is not yet available. If WRA later exposes a native event or stream API, the Backend can emit live events without changing the Frontend SSE contract.

## Tech Stack

- Python 3.12
- FastAPI
- Next.js
- React
- TypeScript
- Tailwind CSS
- DeepSeek V4 Flash (`deepseek-v4-flash`)
- DDGS
- web-research-agent v0.2.0

## Quality Baseline

- Backend: 88 tests passed
- Ruff: PASS
- mypy strict: PASS
- pip check: PASS
- Frontend ESLint: PASS
- TypeScript: PASS
- Next.js production build: PASS
- Fake GUI E2E: PASS
- Real GUI → WRA → DeepSeek/DDGS E2E: PASS
- Fresh Python 3.12 installation: PASS

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Local development](docs/local-development.md)
