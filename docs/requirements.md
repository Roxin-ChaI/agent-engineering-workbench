# Requirements

## Project Goal

`Agent Engineering Workbench` 通过统一 Web UI、API 与 Adapter contract 集成相互独立的 AI Agent 工程项目。

版本范围：

- v0.1.0：Workbench Shell 与 WRA Web Research 集成。
- v0.2.0：在保留 WRA 的基础上，新增 PKRA Knowledge Research 集成。

## v0.2.0 Scope

### Backend

- Python 3.12 与 FastAPI Backend。
- Workbench 自有 `RunResult`、Metrics、Trace 与 Sources contract。
- WRAAdapter 与 PKRAAdapter。
- 通过 PKRA 公共 Production Runner API 完成 production wiring。
- request-scoped PKRA runner 生命周期与可靠的 `close()` 清理。
- `POST /api/research/web` 与 `POST /api/research/web/stream`。
- `POST /api/research/knowledge` 与 `POST /api/research/knowledge/stream`。
- Web Research 与 Knowledge Research 的 Fake 本地联调入口。
- 基础请求校验、安全错误响应和本地 CORS 配置。

### Frontend

- Next.js、React、TypeScript 与 Tailwind CSS Workbench Shell。
- `/research/web` 与 `/research/knowledge` 工作区及导航。
- Web 与 Knowledge Research REST/SSE Client。
- Answer、Status、Metrics、Activity 与 Sources / Evidence 展示区域。
- PKRA 空 Trace 和空 Sources 状态的明确展示。
- English / 中文与 Dark / Light 偏好。

### Integrated Projects

- `web-research-agent` v0.2.0。
- `production-knowledge-research-agent` v0.4.0。

两个项目均保持独立仓库。Workbench 仅通过公共 Python API 与 Adapter 边界集成，不复制源码、不导入 PKRA 私有 Runtime，也不通过 subprocess 调用 CLI。

## Contract and Streaming Boundaries

所有前端 Research 页面只依赖 Workbench `RunResult` contract。当前 PKRA 公共结果可以映射 Answer、Iterations、Tool Calls 与 Duration，但没有可无损映射的结构化 Activity Trace 或 Source/Evidence URL，因此 Knowledge Research 当前返回 `trace = []` 与 `sources = []`。这属于 v0.2.0 已知限制，不是运行失败。

WRA 与 PKRA 当前均通过同步运行入口执行。SSE 语义为：发送 `started`，同步执行 Agent，完成后 replay 可用 Trace，最后发送 `completed`、`stopped` 或 `error`。当前不提供原生实时 Token/Tool streaming。

## Non Goals

- 为 PKRA 伪造 Activity Trace 或从 Answer 文本解析 Sources/Evidence。
- 原生实时 Token/Tool streaming。
- 复制或重新实现 WRA/PKRA Agent Runtime、检索、Web Search 或模型逻辑。
- 通过 Workbench 调用 WRA/PKRA CLI 或 subprocess。
- Context Window Compressor、LLM Context Explorer、GitHub Reviewer、Resume Optimizer、Prompt Vault 与 Prompt Engineering Workbench 的真实集成。
- 用户系统、云部署、持久化运行历史、多 Agent 与 MCP。
- OpenAI、Anthropic 等其他 Model Provider 的具体实现。

## Architecture Constraints

Workbench 只负责 UI、Integration、Presentation 与 API 边界。Adapter 必须隔离 Workbench 与集成项目的内部数据结构，并为后续项目提供统一扩展点。

默认 Provider 为 DeepSeek，默认模型为 `deepseek-v4-flash`。Provider 与模型名称通过配置传入，模型创建通过工厂或依赖注入完成。Workbench 自有模型抽象不强行替换 WRA 或 PKRA 已验证的内部模型层。
