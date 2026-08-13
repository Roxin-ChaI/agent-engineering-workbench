# Requirements

## Project Goal

构建 `Agent Engineering Workbench` v0.1.0，即第一版 Web Workbench，并且只接入 `web-research-agent`（WRA）。

## Scope

- Workbench Web UI 基础壳层。
- Sidebar 和 Web Research 页面。
- 基于 Python 3.12 与 FastAPI 的 Backend。
- Workbench Adapter Layer 和 WRA Adapter。
- Web Research 运行结果展示。
- Agent Activity / Trace 展示。
- Metrics 展示。
- REST 接口，以及为后续运行过程流式展示预留的 SSE 接口边界。
- 基础错误处理。
- 统一的 Model Provider / Model Client 抽象边界。
- v0.1.0 默认 Provider 为 DeepSeek、默认模型为 `deepseek-v4-flash`，并且只实现 DeepSeek Adapter。
- Provider 与模型名称通过配置传入，模型创建通过统一工厂或依赖注入完成。

## Non Goals

- PKRA。
- Context Window Compressor。
- LLM Context Explorer。
- GitHub Reviewer。
- Resume Optimizer。
- Prompt Vault。
- Prompt Engineering Workbench。
- 用户系统。
- 云部署。
- 持久化运行历史。
- 多 Agent。
- MCP。
- OpenAI、Anthropic 等其他 Model Provider 的具体实现。
- 复制或重新实现 WRA 的 Agent Runtime、LangChain Runtime、Web Search 或模型逻辑。

## Initial Version Scope

v0.1.0 的范围锁定为只接入 WRA。Frontend 使用 Next.js、React、TypeScript 和 Tailwind CSS；Backend 使用 Python 3.12 和 FastAPI；Frontend 与 Backend 通过 REST 通信，并保留 SSE 接口边界。

Workbench 只负责 UI、Integration、Presentation 和 API 边界。整体调用链为：

`Browser → Frontend → Workbench Backend → Adapter Layer → WRA → Model Abstraction → DeepSeek Adapter → deepseek-v4-flash`

Adapter 必须隔离 Workbench 与 WRA 的内部数据结构，并提供统一扩展点，以便后续版本接入其他项目而不让 Workbench 依赖其内部实现。

Workbench 业务层不得直接依赖 DeepSeek SDK 或具体模型类。DeepSeek 只是 Model Provider / Model Client 抽象的一种实现；Provider 与模型名称不得散落硬编码，必须通过配置传入，模型创建必须通过统一工厂或依赖注入完成。后续替换其他模型时，不应修改 Workbench 核心业务逻辑。v0.1.0 不实现 OpenAI、Anthropic 等其他 Provider，只保留扩展边界。
