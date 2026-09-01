**English** | [简体中文](README.zh-CN.md)

# Agent Engineering Workbench

**Build, run, and inspect production-oriented AI agent workflows from one workspace.**

Agent Engineering Workbench (AEW) is a full-stack workspace that brings several independent AI engineering projects behind one consistent Web interface. It focuses on research agents, context engineering, code review, resume optimization, prompt experimentation, and prompt management without collapsing those projects into a single codebase.

> **Research Agents · RAG · Context Engineering · Evaluation · Developer Tools**

![Version](https://img.shields.io/badge/version-v0.6.1-181717?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-frontend-3178C6?style=flat-square&logo=typescript&logoColor=white)

## Why this project?

AI engineering projects often start as isolated CLIs, libraries, or service prototypes. AEW provides a common application layer for running and inspecting them through stable public contracts while keeping each upstream project independently versioned and testable.

The Workbench does **not** copy upstream source code and does **not** shell out to project CLIs. Integrations are built through explicit adapters and HTTP boundaries.

## Workspaces

| Workspace | What it does | Integrated project |
| --- | --- | --- |
| **Web Research** | Tool-calling web research with answer, activity, sources, and metrics | [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent) v0.2.0 |
| **Knowledge Research** | LangGraph-based research over hybrid RAG with optional live web search | [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent) v0.4.0 |
| **Context Lab** | Compare LLM message histories before and after token-budget-aware compression | [`context-window-compressor`](https://github.com/Roxin-ChaI/context-window-compressor) v0.1.0 |
| **GitHub Review** | Read-only AI review of public Pull Requests with structured findings | [`ai-github-reviewer`](https://github.com/Roxin-ChaI/ai-github-reviewer) v0.2.0 |
| **Resume Optimization** | Requirement-aware resume analysis with section-level evidence provenance | [`ai-resume-optimizer`](https://github.com/Roxin-ChaI/ai-resume-optimizer) v0.2.1 |
| **Prompt Workspace** | Controlled prompt experiments plus reusable prompt-library workflows | [`prompt-engineering-workbench`](https://github.com/Roxin-ChaI/prompt-engineering-workbench) v0.2.0 + Prompt Vault API v0.2.0 |

The UI also supports English / Chinese, Dark / Light themes, and persisted navigation preferences.

## Architecture

```text
Browser
  → Next.js Workbench
  → FastAPI
      ├─ WRAAdapter → WRA v0.2.0
      ├─ PKRAAdapter → PKRA v0.4.0 ProductionAgentRunner
      │   ├─ PostgreSQL / pgvector
      │   ├─ DeepSeek V4 Flash
      │   └─ optional DDGS Web Search
      ├─ CWCAdapter → CWC v0.1.0 public compress()
      ├─ GitHubReviewerAdapter → AI GitHub Reviewer v0.2.0
      │   ├─ anonymous GitHub REST GET
      │   └─ DeepSeek V4 Flash
      ├─ ResumeOptimizerAdapter → AI Resume Optimizer v0.2.1 → DeepSeek V4 Flash
      ├─ PromptExperimentAdapter → Prompt Engineering Workbench v0.2.0 → DeepSeek V4 Flash
      └─ PromptVaultHttpClient → Prompt Vault API v0.2.0 → SQLAlchemy persistence
  → Workbench-owned response contracts
  → GUI
```

The Frontend depends only on Workbench-owned TypeScript contracts. Backend adapters translate each project's public API into those contracts, preventing the GUI from depending on private upstream implementation details.

[Read the architecture documentation](docs/architecture.md)

## Quick Start

### 1. Clone

```bash
git clone https://github.com/Roxin-ChaI/agent-engineering-workbench.git
cd agent-engineering-workbench
```

### 2. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Start the backend

Create a Python 3.12 environment, install the backend dependencies, configure the required environment variables, and run the FastAPI application.

Because production workspaces have different external dependencies—such as DeepSeek, PostgreSQL/pgvector, or Prompt Vault—the exact setup is documented separately:

**[Local Development Guide](docs/local-development.md)**

For UI work and integration development, the repository also supports fake/local integration paths that avoid real model calls.

## Engineering Highlights

- Stable adapter contracts between independent repositories and the GUI
- REST APIs across all workspaces and SSE replay boundaries for Research workflows
- LangGraph-backed production knowledge research integration
- Hybrid PostgreSQL / pgvector retrieval and optional web search
- Deterministic context-compression and prompt-evaluation paths
- Read-only GitHub PR review boundary with safe server-side failure diagnostics
- Provider secrets kept on the Backend
- Fake integration mode for deterministic development and testing
- English / Chinese UI and Dark / Light themes

## Quality Baseline — v0.6.1

| Area | Status |
| --- | --- |
| Backend tests | **520 passed** |
| GitHub Review focused tests | **67 passed** |
| Prompt Library focused Fake E2E | **12 passed** |
| Frontend tests | **34 passed** |
| Ruff | **PASS** |
| mypy | **PASS** |
| pip check | **PASS** |
| ESLint | **PASS** |
| TypeScript | **PASS** |
| Next.js production build | **PASS** |
| Prompt Library manual visual verification | **PASS** |

Real GUI / REST validation has also been performed for Context Lab, public GitHub PR Review, Resume provenance, Prompt Experiment with `deepseek-v4-flash`, and Prompt Library persistence / failure isolation. GitHub Review failures record only a safe category, root exception type, and optional integer upstream status; messages, bodies, URLs, headers, and API keys are excluded.

## Current Limitations

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
- [Local Development](docs/local-development.md)
- [Changelog](CHANGELOG.md)

## Related Projects

AEW is the application layer for a collection of independently maintained AI engineering projects:

- [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent)
- [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent)
- [`context-window-compressor`](https://github.com/Roxin-ChaI/context-window-compressor)
- [`ai-github-reviewer`](https://github.com/Roxin-ChaI/ai-github-reviewer)
- [`ai-resume-optimizer`](https://github.com/Roxin-ChaI/ai-resume-optimizer)
- [`prompt-engineering-workbench`](https://github.com/Roxin-ChaI/prompt-engineering-workbench)
- [`prompt-vault-api`](https://github.com/Roxin-ChaI/prompt-vault-api)

## License

This project is licensed under the [MIT License](LICENSE).

The integrated upstream projects remain independently licensed; review their respective licenses when reusing or redistributing them.

---

If this project is useful to your own AI agent engineering workflow, consider starring the repository so you can follow future releases.
