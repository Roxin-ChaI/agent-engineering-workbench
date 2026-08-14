# Agent Engineering Workbench

一个用于统一管理和展示 AI Agent 工程项目的 Web Workbench。

## v0.1.0

第一版只接入 `web-research-agent`（WRA），提供 Web Research 页面以及运行结果、Agent Activity / Trace 和 Metrics 展示。

技术栈：Frontend 使用 Next.js、React、TypeScript 和 Tailwind CSS；Backend 使用 Python 3.12 和 FastAPI；接口采用 REST，并通过 SSE 为后续运行过程流式展示预留边界。

调用链固定为：

`Browser → Frontend → Workbench Backend → Adapter Layer → WRA → Model Abstraction → DeepSeek Adapter → deepseek-v4-flash`

Workbench 仅负责 UI、Integration、Presentation 和 API 边界。它不会复制或重新实现 WRA 的 Agent Runtime、LangChain Runtime、Web Search 或模型逻辑。Adapter 隔离 Workbench 与 WRA 内部数据结构，并为后续项目提供统一扩展点。

模型通过统一的 Model Provider / Model Client 抽象接入。v0.1.0 的默认 Provider 为 DeepSeek、默认模型为 `deepseek-v4-flash`，且只实现 DeepSeek Adapter。Provider 与模型名称由配置传入，模型实例通过统一工厂或依赖注入创建；Workbench 核心业务逻辑不依赖 DeepSeek SDK 或具体模型类。当前版本不实现其他 Provider，只保留可替换扩展边界。

详细范围与架构约束参见 [`docs/requirements.md`](docs/requirements.md) 和 [`docs/architecture.md`](docs/architecture.md)。

本地 Fake/Real WRA 运行方式参见 [`docs/local-development.md`](docs/local-development.md)。
