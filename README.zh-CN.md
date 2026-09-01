[English](README.md) | **简体中文**

# Agent Engineering Workbench

**在一个统一工作台中构建、运行并检查生产导向的 AI Agent 工作流。**

Agent Engineering Workbench（AEW）是一个全栈 AI 工程工作台，通过统一 Web 界面整合多个彼此独立的 AI 工程项目，覆盖 Research Agent、Context Engineering、代码审查、简历优化、Prompt Experiment 与 Prompt Library，同时保持各上游项目独立版本化和独立测试。

> **Research Agents · RAG · Context Engineering · Evaluation · Developer Tools**

![Version](https://img.shields.io/badge/version-v0.6.1-181717?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-frontend-3178C6?style=flat-square&logo=typescript&logoColor=white)

## 为什么做这个项目？

AI 工程项目往往以彼此独立的 CLI、库或服务原型存在。AEW 提供统一应用层，通过稳定公共契约运行和检查这些项目，同时不破坏各项目原有的独立性。

Workbench **不复制上游源码**，也**不通过 subprocess 调用各项目 CLI**。所有集成都通过显式 Adapter 或 HTTP Boundary 完成。

## 工作区

| 工作区 | 功能 | 集成项目 |
| --- | --- | --- |
| **Web Research** | Tool Calling Web Research，展示 Answer、Activity、Sources 与 Metrics | [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent) v0.2.0 |
| **Knowledge Research** | 基于 LangGraph 的 Hybrid RAG Research，可选实时 Web Search | [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent) v0.4.0 |
| **Context Lab** | 对比 LLM 消息历史在 Token Budget 压缩前后的变化 | [`context-window-compressor`](https://github.com/Roxin-ChaI/context-window-compressor) v0.1.0 |
| **GitHub Review** | 只读审查公开 Pull Request，输出结构化 Findings | [`ai-github-reviewer`](https://github.com/Roxin-ChaI/ai-github-reviewer) v0.2.0 |
| **Resume Optimization** | 基于职位要求优化简历，并展示章节级证据 provenance | [`ai-resume-optimizer`](https://github.com/Roxin-ChaI/ai-resume-optimizer) v0.2.1 |
| **Prompt Workspace** | 受控 Prompt Experiment + 可复用 Prompt Library | [`prompt-engineering-workbench`](https://github.com/Roxin-ChaI/prompt-engineering-workbench) v0.2.0 + Prompt Vault API v0.2.0 |

UI 同时支持中英文、Dark / Light Theme，以及持久化导航偏好。

## 架构

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

Frontend 只依赖 Workbench 自己的 TypeScript Contracts。Backend Adapter 将各项目公共 API 转换为这些统一契约，因此 GUI 不依赖上游项目私有实现细节。

[查看完整架构文档](docs/architecture.md)

## 快速开始

### 1. Clone

```bash
git clone https://github.com/Roxin-ChaI/agent-engineering-workbench.git
cd agent-engineering-workbench
```

### 2. 启动 Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. 启动 Backend

创建 Python 3.12 环境，安装 Backend 依赖，配置所需环境变量并启动 FastAPI。

由于不同生产工作区依赖不同的外部组件，例如 DeepSeek、PostgreSQL / pgvector 或 Prompt Vault，因此完整配置步骤集中在：

**[本地开发指南](docs/local-development.md)**

对于 UI 和 Integration 开发，仓库也提供 Fake / Local Integration 路径，可避免真实模型调用。

## 工程亮点

- 独立仓库与 GUI 之间使用稳定 Adapter Contracts
- 所有工作区提供 REST API，Research 工作流提供 SSE Replay Boundary
- LangGraph 驱动的 Production Knowledge Research 集成
- PostgreSQL / pgvector Hybrid Retrieval 与可选 Web Search
- 确定性 Context Compression 与 Prompt Evaluation
- 带安全服务端失败诊断的只读 GitHub Pull Request Review Boundary
- Provider Secret 始终保留在 Backend
- Fake Integration Mode 支持确定性开发与测试
- 中英文 UI 与 Dark / Light Theme

## v0.6.1 质量基线

| 项目 | 状态 |
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
| Prompt Library 人工视觉验证 | **PASS** |

Context Lab、公开 GitHub PR Review、Resume provenance、使用 `deepseek-v4-flash` 的 Prompt Experiment，以及 Prompt Library 的持久化与故障隔离均完成过真实 GUI / REST 验证。GitHub Review 失败只记录安全的 category、root exception type 与可选整数 upstream status；不记录 message、body、URL、header 或 API key。

## 当前限制

- Context Token 数值为估算值，并非精确 Tokenizer 计数。
- `compression_applied=true` 表示压缩管线执行，不一定代表输出变化。
- Context HTTP 422 响应含有用的预算详情，但当前 Frontend 仅显示 `Unable to compress this context.`。
- Workbench 不暴露 CWC 私有 partition/change 原因。
- Context Lab 当前没有 persistence 或 SSE。
- PKRA 结构化 Sources/Evidence 与 Activity Trace 当前未映射。
- Research SSE 在同步执行后 replay 可用事件，尚无原生实时 streaming。
- Prompt Experiment 每次只运行一个任务和一个所选 variant，不提供自动对比矩阵。
- Prompt Library 暂无 pagination、authentication/multi-user workflow、prompt history/version history、experiment-result persistence 或 template-variable system。
- Prompt Experiment 没有任意 callable tools；required-tool 条件 fail closed。
- Prompt 评估是确定性二元评估，无部分得分，也没有语义 LLM judge。

## 文档

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Local Development](docs/local-development.md)
- [Changelog](CHANGELOG.md)

## 相关项目

AEW 是一组独立 AI 工程项目之上的应用层：

- [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent)
- [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent)
- [`context-window-compressor`](https://github.com/Roxin-ChaI/context-window-compressor)
- [`ai-github-reviewer`](https://github.com/Roxin-ChaI/ai-github-reviewer)
- [`ai-resume-optimizer`](https://github.com/Roxin-ChaI/ai-resume-optimizer)
- [`prompt-engineering-workbench`](https://github.com/Roxin-ChaI/prompt-engineering-workbench)
- [`prompt-vault-api`](https://github.com/Roxin-ChaI/prompt-vault-api)

## License

仓库级 License 尚未添加。在复用或再分发前，请同时检查各上游集成项目的 License。

---

如果这个项目对你的 AI Agent 工程工作流有帮助，可以 Star 仓库以关注后续版本。
