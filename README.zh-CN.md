[English](README.md) | **简体中文**

# Agent Engineering Workbench

一个通过统一界面集成、运行和检查独立 AI Agent 工程项目的模块化 Web Workbench。

## v0.1.0

第一版只接入一个独立项目：[`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent) v0.2.0。当前版本提供 Workbench 基础壳层与 Web Research 工作区，不复制或重新实现 WRA Runtime、模型接入和搜索逻辑。

## 功能

- Web Research 工作流
- 最终 Answer 展示
- Agent Activity / Trace replay
- 迭代次数、工具调用次数与 WRA 执行耗时 Metrics
- 结构化 Sources
- English / 中文 UI
- 可持久化偏好的 Dark / Light 主题
- Fake 本地联调模式与正式 WRA 集成

v0.1.0 范围外的模块仍为占位页面，不作为已完成集成描述。

## 架构

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

WRA 保持独立仓库，并通过固定 v0.2.0 的 Git 依赖实现可复现安装。Workbench 不复制 WRA 源码。`WRAAdapter` 将 WRA 公共结果 DTO 映射为 Workbench 自有的 `RunResult` contract；Adapter contract 同时为后续其他项目接入提供扩展边界。

## SSE 语义

当前 WRA `run()` 是同步接口。v0.1.0 的 `/api/research/web/stream` 通过 SSE：

1. 发送 `started`；
2. 执行 WRA；
3. WRA 完成后按顺序 replay trace；
4. 发送唯一的 `completed`、`stopped` 或 `error` terminal event。

当前尚不支持原生实时 Agent/Tool streaming。若 WRA 后续提供原生 event 或 stream API，Backend 可在不改变 Frontend SSE contract 的前提下升级为实时事件。

## 技术栈

- Python 3.12
- FastAPI
- Next.js
- React
- TypeScript
- Tailwind CSS
- DeepSeek V4 Flash（`deepseek-v4-flash`）
- DDGS
- web-research-agent v0.2.0

## 质量基线

- Backend：88 tests passed
- Ruff：PASS
- mypy strict：PASS
- pip check：PASS
- Frontend ESLint：PASS
- TypeScript：PASS
- Next.js production build：PASS
- Fake GUI E2E：PASS
- Real GUI → WRA → DeepSeek/DDGS E2E：PASS
- Fresh Python 3.12 installation：PASS

## 文档

- [需求](docs/requirements.md)
- [架构](docs/architecture.md)
- [本地开发](docs/local-development.md)
